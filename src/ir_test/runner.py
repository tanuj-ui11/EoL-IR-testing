from __future__ import annotations

from datetime import datetime, timezone

from .instruments import Instrument
from .models import Measurement, Recipe, Step, StepResult, TestRecord, Verdict


class InterlockOpen(RuntimeError):
    """Raised when HV would be applied with the safety lid open."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def judge(step: Step, m: Measurement) -> Verdict:
    if m.breakdown or m.leakage_ma < 0 or m.leakage_ma >= step.trip_ma:
        return Verdict.FAIL
    return Verdict.PASS


class Session:
    """One charger, one recipe. Stops at the first failing step."""

    def __init__(self, recipe: Recipe, serial: str, operator: str,
                 instrument: Instrument, station_id: str = "IR-01"):
        if not serial.strip():
            raise ValueError("serial is required")
        self.recipe, self.instrument = recipe, instrument
        self.index = 0
        self.record = TestRecord(serial.strip(), recipe.id, operator.strip(),
                                 station_id, _now())

    @property
    def finished(self) -> bool:
        return self.record.verdict is not None

    @property
    def current_step(self) -> Step | None:
        return None if self.finished else self.recipe.steps[self.index]

    def _record(self, m: Measurement, lid_closed: bool) -> StepResult:
        if self.finished:
            raise RuntimeError("test already finished")
        if not lid_closed:
            raise InterlockOpen("close the safety lid before applying high voltage")
        s = self.current_step
        if m.leakage_ma < 0:
            raise ValueError("leakage must be >= 0")
        v = judge(s, m)
        r = StepResult(s.id, s.title, s.voltage_v, s.dwell_s, s.trip_ma, m.leakage_ma,
                       m.breakdown, v,
                       round(s.voltage_v / m.leakage_ma, 1) if m.leakage_ma > 0 else None,
                       m.source, _now())
        self.record.steps.append(r)
        if v is Verdict.FAIL:
            self._finish(Verdict.FAIL)
        else:
            self.index += 1
            if self.index >= len(self.recipe.steps):
                self._finish(Verdict.PASS)
        return r

    def run_current(self, lid_closed: bool) -> StepResult:
        """Automatic instruments only."""
        if not lid_closed:
            raise InterlockOpen("close the safety lid before applying high voltage")
        m = self.instrument.measure(self.current_step)
        if m is None:
            raise RuntimeError("instrument is manual: use submit_manual()")
        return self._record(m, lid_closed)

    def submit_manual(self, leakage_ma: float, breakdown: bool, lid_closed: bool) -> StepResult:
        return self._record(Measurement(float(leakage_ma), bool(breakdown), "manual"), lid_closed)

    def abort(self) -> None:
        if not self.finished:
            self._finish(Verdict.ABORT)

    def _finish(self, v: Verdict) -> None:
        self.record.verdict, self.record.finished_at = v, _now()
