# EoL-IR-testing

End-of-line insulation / dielectric-withstand test module for chargers, built around the
**CC2670P AC withstand-voltage tester** (the grey bench unit with the red HV probe).

Three deliverables:

| Part | Where | Status |
|---|---|---|
| Operator GUI + result logging | `src/ir_test/`, `recipes/` | Working; 8 unit tests + browser run pass (manual + simulator modes) |
| Interlocked test enclosure | `hardware/enclosure/`, `docs/02-enclosure.md` | **Draft, not rendered or measured.** Charger size is estimated from a photo |
| Non-conducting mat | `docs/03-mat-spec.md` | Spec only. The existing green mat's rating is unknown |

## Important: what this instrument actually measures

The CC2670P is a **hipot** tester. It applies kV and trips on **leakage current** (2 mA / 20 mA switch).
It does not read megohms. So the pass/fail here is "no breakdown and leakage < trip limit".
The GUI also shows apparent insulation (V/I) but that is indicative only. If you need a true
IR value in MΩ (e.g. 500 V DC), add a megohmmeter as a second instrument; the driver interface supports it.
See `docs/00-assumptions-and-open-questions.md`.

## Run the GUI

```bash
pip install -e .            # no runtime dependencies
python -m ir_test --instrument manual      # operator reads mA off the CC2670P and types it in
python -m ir_test --instrument simulator   # fake instrument for development / demos
# open http://127.0.0.1:8080
python -m pytest            # tests (pip install -e .[dev])
```

Results are appended to `results/ir_results.jsonl` (full record) and `results/ir_results.csv` (one row per step).
Test steps, voltages and limits live in `recipes/*.json`. **The shipped values are placeholders: confirm them
against your product safety standard before use.**

## Docs

- `docs/00-assumptions-and-open-questions.md`: read first
- `docs/01-test-procedure-and-safety.md`: wiring and operator procedure
- `docs/02-enclosure.md`: enclosure concept, cut list, interlock wiring
- `docs/03-mat-spec.md`: insulating mat requirements
- `docs/04-eol-integration.md`: how this plugs into the EOL GUI later
