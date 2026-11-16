# Integrating with the EOL GUI

Two options, both supported without code changes to this module:

1. **In-process (Python)**: `from ir_test.server import Station`. The EOL GUI creates a `Station` and calls
   `start()`, `manual()`/`run()`, `abort()`, `state()`. `state()` returns plain JSON-able dicts.
2. **HTTP**: run `python -m ir_test` and embed `http://host:8080` in an iframe/panel, or call its JSON API:
   `GET /api/state`, `GET /api/history`, `POST /api/start|lid|run|measurement|abort`.

Result schema (`TestRecord.to_dict()`): `serial, recipe_id, operator, station_id, started_at, finished_at,
verdict (PASS|FAIL|ABORT), steps[]` where each step has voltage, dwell, trip limit, `leakage_ma`, `breakdown`,
step verdict, `apparent_kohm`, `source`. Keep this schema stable; the EOL GUI should join on `serial`.

New instrument (e.g. RS-232 CC2670P or a megohmmeter): subclass `ir_test.instruments.Instrument`,
implement `measure(step)` and optionally `lid_closed()`. No other code changes.
