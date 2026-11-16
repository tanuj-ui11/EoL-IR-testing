from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import TestRecord

CSV_FIELDS = ["finished_at", "station_id", "serial", "recipe_id", "operator", "verdict",
              "step_id", "voltage_v", "dwell_s", "trip_ma", "leakage_ma", "breakdown",
              "step_verdict", "apparent_kohm", "source"]


class ResultStore:
    """Append-only JSONL (full record) + flat CSV (one row per step)."""

    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.jsonl, self.csv = self.dir / "ir_results.jsonl", self.dir / "ir_results.csv"

    def save(self, rec: TestRecord) -> None:
        d = rec.to_dict()
        with self.jsonl.open("a") as f:
            f.write(json.dumps(d) + "\n")
        new = not self.csv.exists()
        with self.csv.open("a", newline="") as f:
            w = csv.DictWriter(f, CSV_FIELDS)
            if new:
                w.writeheader()
            for s in d["steps"]:
                w.writerow({"finished_at": d["finished_at"], "station_id": d["station_id"],
                            "serial": d["serial"], "recipe_id": d["recipe_id"],
                            "operator": d["operator"], "verdict": d["verdict"],
                            "step_id": s["step_id"], "voltage_v": s["voltage_v"],
                            "dwell_s": s["dwell_s"], "trip_ma": s["trip_ma"],
                            "leakage_ma": s["leakage_ma"], "breakdown": s["breakdown"],
                            "step_verdict": s["verdict"], "apparent_kohm": s["apparent_kohm"],
                            "source": s["source"]})

    def history(self, limit: int = 20) -> list[dict]:
        if not self.jsonl.exists():
            return []
        lines = self.jsonl.read_text().splitlines()[-limit:]
        return [json.loads(x) for x in reversed(lines)]
