"""Anomaly / fraud detection for flexibility claims."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import FraudAlert, MeterReading, Participant


def verify_flexibility_claim(
    db: Session,
    participant_id: str,
    claimed_kwh: float,
    observed_delta_kwh: float | None = None,
    transaction_id: str | None = None,
) -> FraudAlert | None:
    """
    Flag unrealistic claims.

    Example: claim 500 kWh flexibility but meter shows ~20 kWh change.
    """
    participant = db.query(Participant).filter(Participant.id == participant_id).first()
    if not participant:
        return None

    if observed_delta_kwh is None:
        # Estimate from recent readings variance if available
        meter = participant.meters[0] if participant.meters else None
        if meter and meter.readings:
            powers = [r.power_kw for r in meter.readings[-24:]]
            if len(powers) >= 2:
                observed_delta_kwh = max(0.0, (max(powers) - min(powers)) * 2)
            else:
                observed_delta_kwh = participant.flexible_kw + participant.curtailable_kw
        else:
            # Capacity-based plausibility bound
            observed_delta_kwh = (participant.flexible_kw + participant.curtailable_kw) * 4

    max_plausible = (participant.flexible_kw + participant.curtailable_kw + participant.solar_kw) * 6
    alerts: list[FraudAlert] = []

    if claimed_kwh > max(observed_delta_kwh * 3, 1.0) or claimed_kwh > max_plausible * 1.5:
        alert = FraudAlert(
            participant_id=participant_id,
            transaction_id=transaction_id,
            alert_type="invalid_flexibility_claim",
            severity="high",
            message=(
                f"Potentially invalid flexibility claim. Claimed {claimed_kwh:.1f} kWh "
                f"but meter/capacity evidence suggests ~{observed_delta_kwh:.1f} kWh."
            ),
            claimed_kwh=claimed_kwh,
            observed_kwh=observed_delta_kwh,
        )
        db.add(alert)
        alerts.append(alert)

    if participant.solar_kw > 0 and claimed_kwh > participant.solar_kw * 12:
        alert = FraudAlert(
            participant_id=participant_id,
            transaction_id=transaction_id,
            alert_type="unrealistic_generation",
            severity="medium",
            message="Sudden unrealistic generation/flexibility relative to solar capacity.",
            claimed_kwh=claimed_kwh,
            observed_kwh=participant.solar_kw * 5,
        )
        db.add(alert)
        alerts.append(alert)

    db.commit()
    return alerts[0] if alerts else None


def detect_meter_anomalies(db: Session, meter_id: str) -> list[FraudAlert]:
    readings = (
        db.query(MeterReading)
        .filter(MeterReading.meter_id == meter_id)
        .order_by(MeterReading.ts.desc())
        .limit(48)
        .all()
    )
    alerts: list[FraudAlert] = []
    if not readings:
        return alerts

    # Duplicate timestamps / identical sequences
    seen_ts = set()
    for r in readings:
        key = (r.ts.isoformat(), round(r.power_kw, 4))
        if key in seen_ts:
            alert = FraudAlert(
                alert_type="duplicate_readings",
                severity="low",
                message="Duplicate meter readings detected.",
                claimed_kwh=None,
                observed_kwh=r.power_kw,
            )
            db.add(alert)
            alerts.append(alert)
            break
        seen_ts.add(key)

    # Impossible jumps
    powers = list(reversed([r.power_kw for r in readings]))
    for i in range(1, len(powers)):
        if abs(powers[i] - powers[i - 1]) > max(50.0, powers[i - 1] * 5):
            alert = FraudAlert(
                alert_type="meter_manipulation",
                severity="high",
                message="Impossible energy step-change between consecutive readings.",
                claimed_kwh=powers[i],
                observed_kwh=powers[i - 1],
            )
            db.add(alert)
            alerts.append(alert)
            break

    db.commit()
    return alerts