"""Instrument drivers.

measure() returns a Measurement, or None when the operator must read the
instrument display and type the value in (manual mode).
lid_closed() returns the hardware interlock state, or None when no hardware
interlock is wired (operator confirms instead).
"""
from __future__ import annotations

import random
from abc import ABC, abstractmethod

from .models import Measurement, Step


class Instrument(ABC):
    name = "instrument"

    @property
    def manual(self) -> bool:
        return False

    def lid_closed(self) -> bool | None:
        return None

    @abstractmethod
    def measure(self, step: Step) -> Measurement | None: ...


class ManualInstrument(Instrument):
    """CC2670P driven by hand: operator presses START, reads mA, types it in."""
    name = "CC2670P (manual)"

    @property
    def manual(self) -> bool:
        return True

    def measure(self, step: Step) -> Measurement | None:
        return None


class SimulatorInstrument(Instrument):
    name = "Simulator"

    def __init__(self, fault_rate: float = 0.15, seed: int | None = None):
        self.fault_rate = fault_rate
        self._rng = random.Random(seed)

    def measure(self, step: Step) -> Measurement:
        if self._rng.random() < self.fault_rate:
            return Measurement(leakage_ma=step.trip_ma, breakdown=True, source="simulator")
        base = step.trip_ma * self._rng.uniform(0.02, 0.25)
        return Measurement(leakage_ma=round(base, 3), source="simulator")
