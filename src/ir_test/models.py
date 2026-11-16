from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ABORT = "ABORT"


@dataclass(frozen=True)
class Step:
    id: str
    title: str
    instruction: str      # what the operator must connect
    voltage_v: float      # AC test voltage, V rms
    dwell_s: float        # time at voltage, s
    trip_ma: float        # leakage limit, mA (set the CC2670P to the same value)


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    steps: tuple[Step, ...]

    @classmethod
    def from_dict(cls, d: dict) -> "Recipe":
        return cls(d["id"], d["name"], tuple(Step(**s) for s in d["steps"]))

    @classmethod
    def load_all(cls, directory: Path) -> dict[str, "Recipe"]:
        out = {}
        for p in sorted(Path(directory).glob("*.json")):
            r = cls.from_dict(json.loads(p.read_text()))
            out[r.id] = r
        return out


@dataclass
class Measurement:
    leakage_ma: float
    breakdown: bool = False
    source: str = "manual"


@dataclass
class StepResult:
    step_id: str
    title: str
    voltage_v: float
    dwell_s: float
    trip_ma: float
    leakage_ma: float
    breakdown: bool
    verdict: Verdict
    apparent_kohm: float | None   # V/I, indicative only: hipot is not an IR meter
    source: str
    timestamp: str


@dataclass
class TestRecord:
    """Stable result schema; this is what the EOL GUI will consume."""
    serial: str
    recipe_id: str
    operator: str
    station_id: str
    started_at: str
    finished_at: str | None = None
    verdict: Verdict | None = None
    steps: list[StepResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return json.loads(json.dumps(asdict(self), default=lambda o: o.value))
