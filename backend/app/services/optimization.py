"""Smart load-shifting optimization (heuristic prototype)."""

from __future__ import annotations

from app.schemas import LoadShiftRequest, LoadShiftResult


def optimize_load_shift(req: LoadShiftRequest) -> LoadShiftResult:
    """
    Move a named appliance (e.g. EV) from evening peak to midday solar window.
    Builds 24-hour before/after curves from appliance schedule assumptions.
    """
    before = [0.0] * 24
    # Spread baseload-like continuous appliances
    continuous = {"AC", "WaterHeater", "Lighting", "Other"}
    for name, kw in req.appliances.items():
        if name == req.shift_appliance:
            start, end = req.peak_window
            for h in range(start, end):
                before[h % 24] += kw
        elif name in continuous or name in {"AC", "Water heater", "WaterHeater"}:
            for h in range(24):
                # Daytime AC heavier
                factor = 1.0 if 12 <= h <= 22 else 0.4
                before[h] += kw * factor / 3.0
        else:
            # Default evening bias
            for h in (7, 8, 19, 20, 21):
                before[h] += kw / 5.0

    after = before.copy()
    shift_kw = req.appliances.get(req.shift_appliance, 0.0)
    p0, p1 = req.peak_window
    s0, s1 = req.shift_window
    for h in range(p0, p1):
        after[h % 24] = max(0.0, after[h % 24] - shift_kw)
    span = max(1, s1 - s0)
    for h in range(s0, s1):
        after[h % 24] += shift_kw

    before_peak = max(before[p0:p1]) if p1 > p0 else max(before)
    after_peak = max(after[p0:p1]) if p1 > p0 else max(after)

    narrative = (
        f"{req.shift_appliance} charging/load moved from {p0:02d}:00–{p1:02d}:00 "
        f"to {s0:02d}:00–{s1:02d}:00 when solar/grid capacity is typically higher. "
        f"Evening peak reduced by {before_peak - after_peak:.1f} kW."
    )
    return LoadShiftResult(
        before_curve=[round(x, 3) for x in before],
        after_curve=[round(x, 3) for x in after],
        before_peak_kw=round(before_peak, 3),
        after_peak_kw=round(after_peak, 3),
        peak_reduction_kw=round(before_peak - after_peak, 3),
        narrative=narrative,
    )