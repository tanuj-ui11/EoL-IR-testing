"""Device readers + HTTP delivery loop.

    python -m scan_forwarder --device /dev/input/by-id/usb-...-event-kbd --url https://.../scan
    python -m scan_forwarder --serial /dev/ttyACM0 --url ...
    python -m scan_forwarder --stdin --url ...            # type or pipe codes, one per line (bench testing)

The bearer token, if any, is read from the SCAN_WEBHOOK_TOKEN environment variable (never the command line,
which other users on the box can see in `ps`).
"""
from __future__ import annotations

import argparse
import json
import os
import select
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .core import Assembler, Debouncer, Spool, clean, make_payload

EV_KEY = 1
EVIOCGRAB = 0x40044590  # _IOW('E', 0x90, int)
_EVENT = struct.Struct("llHHi")  # struct input_event: kernel uses native longs for the timestamp


class EvdevReader:
    """Reads one HID-keyboard scanner and grabs it exclusively, so its keystrokes never reach the browser."""

    def __init__(self, path: str, grab: bool = True):
        import fcntl
        self.fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        if grab:
            fcntl.ioctl(self.fd, EVIOCGRAB, 1)
        self.asm = Assembler()
        self.source = "hid"

    def fileno(self) -> int:
        return self.fd

    def read(self) -> list[str]:
        try:
            data = os.read(self.fd, _EVENT.size * 64)
        except BlockingIOError:
            return []
        if not data:
            raise OSError("scanner disconnected")
        out = []
        for off in range(0, len(data) - _EVENT.size + 1, _EVENT.size):
            _, _, etype, code, value = _EVENT.unpack_from(data, off)
            if etype == EV_KEY:
                scan = self.asm.feed(code, value)
                if scan:
                    out.append(scan)
        return out


class LineReader:
    """USB-COM (CDC-ACM) scanner or stdin: one code per CR/LF-terminated line."""

    def __init__(self, path: str | None):
        if path is None:
            self.fd, self.source = sys.stdin.fileno(), "stdin"
        else:
            import termios
            import tty
            self.fd, self.source = os.open(path, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK), "serial"
            tty.setraw(self.fd)
            attrs = termios.tcgetattr(self.fd)
            attrs[4] = attrs[5] = termios.B9600  # ignored by CDC-ACM; matters for real RS-232 adapters
            termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        self.buf = b""

    def fileno(self) -> int:
        return self.fd

    def read(self) -> list[str]:
        try:
            data = os.read(self.fd, 4096)
        except BlockingIOError:
            return []
        if not data:
            raise EOFError
        self.buf += data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        *lines, self.buf = self.buf.split(b"\n")
        return [ln.decode("utf-8", "replace") for ln in lines if ln.strip()]


def http_sender(url: str, token: str | None, dead_letter: Path, timeout: float = 5.0):
    """send(item) -> True when delivered or permanently rejected (dead-lettered), False to retry later."""
    def send(item: dict) -> bool:
        req = urllib.request.Request(url, data=json.dumps(item).encode(), method="POST",
                                     headers={"Content-Type": "application/json"})
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return 200 <= r.status < 300
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500 and e.code not in (408, 429):
                with dead_letter.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"item": item, "status": e.code}) + "\n")
                log(f"rejected {item['serial']} with HTTP {e.code}; written to {dead_letter}")
                return True
            return False
        except (urllib.error.URLError, OSError):
            return False
    return send


def log(msg: str) -> None:
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def run(reader, spool: Spool, send, station_id: str, debounce: Debouncer, pattern: str | None,
        retry_max_s: float = 60.0, stop=lambda: False) -> None:
    backoff, next_try = 1.0, 0.0
    while not stop():
        ready, _, _ = select.select([reader], [], [], 0.5)
        if ready:
            for raw in reader.read():
                code = clean(raw, pattern)
                if code is None:
                    log(f"ignored scan {raw!r} (empty or does not match --pattern)")
                elif debounce.accept(code):
                    spool.push(make_payload(code, station_id, reader.source))
                    log(f"scanned {code}")
                    next_try = 0.0  # new scan: try right away
        if time.monotonic() >= next_try and spool.path.exists() and spool.path.stat().st_size:
            sent = spool.flush(send)
            left = len(spool)
            if left:
                next_try = time.monotonic() + backoff
                log(f"delivery failing, {left} queued, retry in {backoff:.0f}s")
                backoff = min(backoff * 2, retry_max_s)
            else:
                backoff = 1.0
                if sent:
                    log(f"delivered {sent}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="scan-forwarder", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--device", help="evdev node of the scanner, ideally /dev/input/by-id/...-event-kbd")
    src.add_argument("--serial", help="tty of a USB-COM scanner, e.g. /dev/ttyACM0")
    src.add_argument("--stdin", action="store_true", help="read codes from stdin (testing)")
    ap.add_argument("--url", default=os.environ.get("SCAN_WEBHOOK_URL"),
                    help="webhook to POST each scan to (or env SCAN_WEBHOOK_URL)")
    ap.add_argument("--station-id", default=os.environ.get("STATION_ID", os.uname().nodename))
    ap.add_argument("--spool", default=os.environ.get("SCAN_SPOOL", "/var/lib/scan-forwarder/queue.jsonl"))
    ap.add_argument("--pattern", default=os.environ.get("SCAN_PATTERN"),
                    help="regex a valid serial must fully match, e.g. 'LW[0-9]{8}'")
    ap.add_argument("--debounce", type=float, default=3.0, help="ignore the same code re-read within N seconds")
    ap.add_argument("--no-grab", action="store_true", help="do not take the HID scanner exclusively")
    a = ap.parse_args(argv)
    if not a.url:
        ap.error("--url or SCAN_WEBHOOK_URL is required")

    spool = Spool(Path(a.spool))
    send = http_sender(a.url, os.environ.get("SCAN_WEBHOOK_TOKEN"), spool.path.with_name("rejected.jsonl"))
    if a.device:
        reader = EvdevReader(a.device, grab=not a.no_grab)
    else:
        reader = LineReader(a.serial)
    log(f"station {a.station_id}: {reader.source} -> {a.url} ({len(spool)} queued)")
    try:
        run(reader, spool, send, a.station_id, Debouncer(a.debounce), a.pattern)
    except EOFError:  # stdin closed: one last delivery attempt
        spool.flush(send)
        log(f"stdin closed, {len(spool)} left in {spool.path}")
    except KeyboardInterrupt:
        pass
    except OSError as e:  # unplugged: exit non-zero so systemd restarts us when it is back
        log(f"reader error: {e}")
        sys.exit(1)
