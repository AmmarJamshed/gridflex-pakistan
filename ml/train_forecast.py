"""Train and dump simple forecast artifact metrics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.forecasting import forecast_all, isolation_forest_scores  # noqa: E402


def main() -> None:
    forecasts = forecast_all()
    anomalies = isolation_forest_scores()
    out_dir = ROOT / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "sample_forecasts.json").write_text(
        json.dumps(forecasts, indent=2), encoding="utf-8"
    )
    (out_dir / "sample_anomalies.json").write_text(
        json.dumps(anomalies, indent=2), encoding="utf-8"
    )
    print("Wrote sample_forecasts.json and sample_anomalies.json")


if __name__ == "__main__":
    main()