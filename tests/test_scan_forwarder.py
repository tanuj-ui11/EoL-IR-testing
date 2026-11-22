import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from scan_forwarder.cli import http_sender
from scan_forwarder.core import Assembler, Debouncer, Spool, clean, make_payload

DOWN, UP = 1, 0
KEYS = {"L": 38, "W": 17, "0": 11, "1": 2, "2": 3, "-": 12}


def type_(asm, text, enter=28):
    out = []
    for ch in text:
        shift = ch.isupper() or ch == "_"
        if shift: asm.feed(42, DOWN)
        k = KEYS[ch.upper()] if ch != "_" else 12
        out += [asm.feed(k, DOWN), asm.feed(k, UP)]
        if shift: asm.feed(42, UP)
    out.append(asm.feed(enter, DOWN))
    return [x for x in out if x]


def test_assembler_shift_and_enter():
    assert type_(Assembler(), "LW-0012_") == ["LW-0012_"]


def test_assembler_keypad_enter_and_autorepeat_ignored():
    a = Assembler()
    a.feed(79, DOWN); a.feed(79, 2); a.feed(82, DOWN)          # KP1, repeat, KP0
    assert a.feed(96, DOWN) == "10"
    assert a.feed(28, DOWN) is None                              # empty scan dropped


def test_capslock_inverts_letters_only():
    a = Assembler()
    a.feed(58, DOWN); a.feed(38, DOWN); a.feed(2, DOWN)
    assert a.feed(28, DOWN) == "L1"


def test_debounce_window():
    t = [0.0]
    d = Debouncer(3.0, clock=lambda: t[0])
    assert d.accept("A")
    t[0] = 1.0; assert not d.accept("A")
    t[0] = 2.0; assert d.accept("B")
    t[0] = 6.0; assert d.accept("B")


def test_clean_and_pattern():
    assert clean("  LW00000001\x00\r") == "LW00000001"
    assert clean("   ") is None
    assert clean("LW1", r"LW[0-9]{8}") is None
    assert clean("LW12345678", r"LW[0-9]{8}") == "LW12345678"


def test_spool_keeps_order_and_failed_items(tmp_path):
    s = Spool(tmp_path / "q.jsonl")
    for i in range(3):
        s.push(make_payload(f"S{i}", "ST1", "test"))
    seen = []
    assert s.flush(lambda it: (seen.append(it["serial"]) or len(seen) < 2)) == 1
    assert [i["serial"] for i in s.items()] == ["S1", "S2"]
    assert s.flush(lambda it: True) == 2 and len(s) == 0


def test_spool_survives_torn_line(tmp_path):
    p = tmp_path / "q.jsonl"
    p.write_text(json.dumps({"serial": "A"}) + "\n{\"serial\": \"B")
    assert [i["serial"] for i in Spool(p).items()] == ["A"]


def _server(codes):
    got = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            got.append((body, self.headers.get("Authorization")))
            self.send_response(codes.pop(0)); self.end_headers()

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, got


def test_http_sender_retry_vs_reject(tmp_path):
    srv, got = _server([200, 503, 422])
    dead = tmp_path / "rejected.jsonl"
    send = http_sender(f"http://127.0.0.1:{srv.server_address[1]}/scan", "tok", dead)
    item = make_payload("SN9", "ST1", "test")
    assert send(item) is True and got[0] == (item, "Bearer tok")
    assert send(item) is False                    # 5xx -> keep queued
    assert send(item) is True                     # 4xx -> dead-lettered, not retried forever
    assert json.loads(dead.read_text())["status"] == 422
    srv.shutdown()


def test_http_sender_unreachable_is_retry(tmp_path):
    send = http_sender("http://127.0.0.1:9/scan", None, tmp_path / "d.jsonl", timeout=0.5)
    assert send(make_payload("X", "S", "t")) is False
