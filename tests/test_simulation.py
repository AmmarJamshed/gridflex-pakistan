"""Simulation engine tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import Base, SessionLocal, engine
from app.schemas import SimulationConfig
from app.services.simulation import build_national_curves, run_pakistan_simulation
import numpy as np


def test_national_curves_length():
    rng = np.random.default_rng(0)
    curves = build_national_curves(SimulationConfig(households=1000, commercial=100, industrial=10, solar_systems=200, batteries=50), rng)
    assert len(curves["demand"]) == 24
    assert curves["demand"].max() > curves["demand"].min()
    assert curves["solar"][13] > curves["solar"][2]


def test_gridflex_reduces_peak():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = run_pakistan_simulation(
            db,
            SimulationConfig(
                households=1000,
                commercial=100,
                industrial=10,
                solar_systems=200,
                batteries=50,
                seed=1,
            ),
        )
        assert result.peak_with_mw < result.peak_without_mw
        assert result.peak_reduction_pct > 0
        assert len(result.without_gridflex) == 24
        assert len(result.with_gridflex) == 24
    finally:
        db.close()