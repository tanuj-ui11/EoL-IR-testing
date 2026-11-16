"""Zero-dependency web GUI + JSON API.  python -m ir_test.server --instrument simulator"""
from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .instruments import Instrument, ManualInstrument, SimulatorInstrument
from .models import Recipe
from .runner import InterlockOpen, Session
from .storage import ResultStore

ROOT = Path(__file__).resolve().parents[2]
STATIC = Path(__file__).parent / "static"


class Station:
    """All station state. The future EOL GUI can import this class directly."""

    def __init__(self, instrument: Instrument, recipes: dict[str, Recipe],
                 store: ResultStore, station_id: str = "IR-01"):
        self.instrument, self.recipes, self.store = instrument, recipes, store
        self.station_id = station_id
        self.session: Session | None = None
        self.operator_lid = False
        self.lock = threading.Lock()

    def lid_closed(self) -> bool:
        hw = self.instrument.lid_closed()
        return self.operator_lid if hw is None else hw

    def state(self) -> dict:
        s = self.session
        return {
            "instrument": self.instrument.name, "manual": self.instrument.manual,
            "hw_interlock": self.instrument.lid_closed() is not None,
            "lid_closed": self.lid_closed(), "station_id": self.station_id,
            "recipes": [{"id": r.id, "name": r.name} for r in self.recipes.values()],
            "session": None if s is None else {
                "index": s.index, "finished": s.finished,
                "recipe": {"id": s.recipe.id, "name": s.recipe.name,
                           "steps": [vars(x) for x in s.recipe.steps]},
                "record": s.record.to_dict()},
        }

    def start(self, recipe_id: str, serial: str, operator: str) -> None:
        if self.session and not self.session.finished:
            raise RuntimeError("a test is already running; abort it first")
        self.operator_lid = False
        self.session = Session(self.recipes[recipe_id], serial, operator,
                               self.instrument, self.station_id)

    def _need(self) -> Session:
        if not self.session or self.session.finished:
            raise RuntimeError("no active test")
        return self.session

    def _after(self) -> None:
        self.operator_lid = False  # leads must be re-clipped between steps
        if self.session and self.session.finished:
            self.store.save(self.session.record)

    def run(self) -> None:
        self._need().run_current(self.lid_closed()); self._after()

    def manual(self, leakage_ma: float, breakdown: bool) -> None:
        self._need().submit_manual(leakage_ma, breakdown, self.lid_closed()); self._after()

    def abort(self) -> None:
        if self.session and not self.session.finished:
            self.session.abort(); self._after()


def make_handler(st: Station):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _json(self, obj, code=200):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers(); self.wfile.write(b)

        def do_GET(self):
            if self.path == "/api/state":
                with st.lock: return self._json(st.state())
            if self.path.startswith("/api/history"):
                with st.lock: return self._json(st.store.history())
            if self.path in ("/", "/index.html"):
                b = (STATIC / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(b)))
                self.end_headers(); return self.wfile.write(b)
            self.send_error(404)

        def do_POST(self):
            n = int(self.headers.get("Content-Length") or 0)
            d = json.loads(self.rfile.read(n) or b"{}")
            try:
                with st.lock:
                    p = self.path
                    if p == "/api/start": st.start(d["recipe"], d.get("serial", ""), d.get("operator", ""))
                    elif p == "/api/lid": st.operator_lid = bool(d.get("closed"))
                    elif p == "/api/run": st.run()
                    elif p == "/api/measurement": st.manual(float(d["leakage_ma"]), bool(d.get("breakdown")))
                    elif p == "/api/abort": st.abort()
                    else: return self.send_error(404)
                    return self._json(st.state())
            except InterlockOpen as e:
                return self._json({"error": str(e), "interlock": True}, 409)
            except (KeyError, ValueError, RuntimeError) as e:
                return self._json({"error": str(e)}, 400)
    return H


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--instrument", choices=["manual", "simulator"], default="manual")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--recipes", default=str(ROOT / "recipes"))
    ap.add_argument("--results", default=str(ROOT / "results"))
    a = ap.parse_args(argv)
    inst = SimulatorInstrument() if a.instrument == "simulator" else ManualInstrument()
    st = Station(inst, Recipe.load_all(Path(a.recipes)), ResultStore(Path(a.results)))
    print(f"IR test station on http://{a.host}:{a.port}  ({inst.name})")
    ThreadingHTTPServer((a.host, a.port), make_handler(st)).serve_forever()


if __name__ == "__main__":
    main()
