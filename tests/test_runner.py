import pytest

from ir_test import InterlockOpen, Recipe, Session, Verdict
from ir_test.instruments import ManualInstrument, SimulatorInstrument
from ir_test.storage import ResultStore
from pathlib import Path

RECIPE = Recipe.load_all(Path(__file__).parents[1] / "recipes")["charger_class1"]


def mk(inst=None):
    return Session(RECIPE, "SN1", "op", inst or ManualInstrument())


def test_pass_both_steps():
    s = mk()
    s.submit_manual(0.8, False, True)
    assert not s.finished
    s.submit_manual(1.2, False, True)
    assert s.record.verdict is Verdict.PASS and len(s.record.steps) == 2
    assert s.record.steps[0].apparent_kohm == 1500 / 0.8


def test_limit_is_fail_and_stops_early():
    s = mk()
    s.submit_manual(5.0, False, True)       # at the trip limit = fail
    assert s.record.verdict is Verdict.FAIL and len(s.record.steps) == 1


def test_breakdown_fails():
    s = mk()
    s.submit_manual(0.1, True, True)
    assert s.record.verdict is Verdict.FAIL


def test_interlock_blocks_hv():
    s = mk()
    with pytest.raises(InterlockOpen):
        s.submit_manual(0.1, False, False)
    assert not s.record.steps


def test_cannot_run_on_manual_instrument():
    with pytest.raises(RuntimeError):
        mk().run_current(True)


def test_simulator_runs_to_a_verdict():
    s = mk(SimulatorInstrument(fault_rate=0, seed=1))
    s.run_current(True); s.run_current(True)
    assert s.record.verdict is Verdict.PASS


def test_abort_and_serial_required():
    s = mk(); s.abort()
    assert s.record.verdict is Verdict.ABORT
    with pytest.raises(ValueError):
        Session(RECIPE, " ", "op", ManualInstrument())


def test_store_roundtrip(tmp_path):
    s = mk(); s.submit_manual(0.5, False, True); s.submit_manual(0.5, False, True)
    st = ResultStore(tmp_path); st.save(s.record)
    assert st.history()[0]["verdict"] == "PASS"
    assert len(st.csv.read_text().splitlines()) == 3
