"""CLI: run Pakistan GridFlex simulation offline and write sample JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import SessionLocal, init_db  # noqa: E402
from app.schemas import SimulationConfig  # noqa: E402
from app.services.simulation import run_pakistan_simulation  # noqa: E402


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        result = run_pakistan_simulation(db, SimulationConfig())
        out = ROOT / "data" / "sample_simulation.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(f"Wrote {out}")
        print(
            f"Peak {result.peak_without_mw} -> {result.peak_with_mw} MW "
            f"({result.peak_reduction_pct}% reduction)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()