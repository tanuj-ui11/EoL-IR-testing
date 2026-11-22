"""Pure logic: key decoding, scan assembly, de-duplication, durable spool. No I/O to devices here."""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

# Linux input-event key codes -> (unshifted, shifted), US layout. Scanners in HID mode send US layout by default.
_ROWS = {
    2: "1!", 3: "2@", 4: "3#", 5: "4$", 6: "5%", 7: "6^", 8: "7&", 9: "8*", 10: "9(", 11: "0)",
    12: "-_", 13: "=+", 26: "[{", 27: "]}", 39: ";:", 40: "'\"", 41: "`~", 43: "\\|",
    51: ",<", 52: ".>", 53: "/?", 57: "  ",
    # keypad (some scanners send digits this way, "Alt+keypad" mode excluded)
    71: "77", 72: "88", 73: "99", 74: "--", 75: "44", 76: "55", 77: "66", 78: "++",
    79: "11", 80: "22", 81: "33", 82: "00", 83: "..", 98: "//", 55: "**",
}
for _code, _ch in zip(list(range(16, 26)) + list(range(30, 39)) + list(range(44, 51)), "qwertyuiopasdfghjklzxcvbnm"):
    _ROWS[_code] = _ch + _ch.upper()

KEY_ENTER, KEY_KPENTER, KEY_TAB = 28, 96, 15
KEY_LEFTSHIFT, KEY_RIGHTSHIFT, KEY_CAPSLOCK = 42, 54, 58
TERMINATORS = {KEY_ENTER, KEY_KPENTER, KEY_TAB}


def decode_key(code: int, shift: bool) -> str | None:
    """Character for a key-down, or None for keys that produce no character."""
    pair = _ROWS.get(code)
    return None if pair is None else pair[1 if shift else 0]


class Assembler:
    """Turns key events (code, value) into complete scans. value: 1 = down, 0 = up, 2 = autorepeat."""

    def __init__(self, max_len: int = 256):
        self.buf: list[str] = []
        self.shift = False
        self.caps = False
        self.max_len = max_len

    def feed(self, code: int, value: int) -> str | None:
        if code in (KEY_LEFTSHIFT, KEY_RIGHTSHIFT):
            self.shift = value != 0
            return None
        if value != 1:  # ignore key-up and autorepeat
            return None
        if code == KEY_CAPSLOCK:
            self.caps = not self.caps
            return None
        if code in TERMINATORS:
            scan, self.buf = "".join(self.buf), []
            return scan or None
        ch = decode_key(code, self.shift)
        if ch is not None:
            if self.caps and ch.isalpha():
                ch = ch.swapcase()
            if len(self.buf) < self.max_len:
                self.buf.append(ch)
        return None


class Debouncer:
    """Drops the same code re-read within `window_s` (fixed-mount scanners re-read a label left in the field)."""

    def __init__(self, window_s: float = 3.0, clock=time.monotonic):
        self.window_s, self.clock = window_s, clock
        self.last: tuple[str, float] | None = None

    def accept(self, code: str) -> bool:
        now = self.clock()
        if self.last and self.last[0] == code and now - self.last[1] < self.window_s:
            self.last = (code, now)
            return False
        self.last = (code, now)
        return True


def clean(raw: str, pattern: str | None = None) -> str | None:
    """Strip whitespace/control chars; return None if empty or not matching `pattern` (full match)."""
    s = "".join(ch for ch in raw if ch.isprintable()).strip()
    if not s:
        return None
    if pattern and not re.fullmatch(pattern, s):
        return None
    return s


def make_payload(code: str, station_id: str, source: str, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    return {"serial": code, "station_id": station_id, "scanned_at": now.isoformat(timespec="milliseconds"),
            "source": source}


class Spool:
    """Append-only JSONL queue on disk. Scans are written here first and removed only after delivery succeeds."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def push(self, item: dict) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def items(self) -> list[dict]:
        if not self.path.exists():
            return []
        out = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # torn last line after power loss
        return out

    def __len__(self) -> int:
        return len(self.items())

    def flush(self, send) -> int:
        """Deliver queued items in order with `send(item) -> bool`. Stops at the first failure. Returns sent count."""
        items = self.items()
        sent = 0
        for item in items:
            if not send(item):
                break
            sent += 1
        if sent:
            rest = items[sent:]
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text("".join(json.dumps(i) + "\n" for i in rest), encoding="utf-8")
            os.replace(tmp, self.path)
        return sent
