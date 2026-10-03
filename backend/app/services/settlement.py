"""Financial settlement / flexibility wallet updates."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import MarketTransaction, Settlement, Wallet


def get_or_create_wallet(db: Session, user_id: str) -> Wallet:
    wallet = db.query(Wallet).filter(Wallet.user_id == user_id).first()
    if wallet:
        return wallet
    wallet = Wallet(user_id=user_id)
    db.add(wallet)
    db.flush()
    return wallet


def apply_settlement(db: Session, tx: MarketTransaction) -> None:
    """Credit seller wallet; record settlement rows. Credits are fiat PKR, not crypto."""
    if tx.seller_user_id:
        wallet = get_or_create_wallet(db, tx.seller_user_id)
        wallet.flexibility_provided_kwh += tx.energy_kwh
        if "reduction" in (tx.meter_evidence or {}).get("flexibility_type", ""):
            wallet.demand_reduction_kwh += tx.energy_kwh
        if (tx.meter_evidence or {}).get("flexibility_type") == "generation_export":
            wallet.solar_surplus_kwh += tx.energy_kwh
        wallet.earnings_pkr += tx.seller_revenue_pkr
        wallet.pending_settlement_pkr += tx.seller_revenue_pkr * 0.2
        wallet.updated_at = datetime.utcnow()
        db.add(
            Settlement(
                transaction_id=tx.id,
                user_id=tx.seller_user_id,
                amount_pkr=tx.seller_revenue_pkr,
                fee_pkr=tx.platform_fee_pkr + tx.grid_fee_pkr,
                direction="credit",
                status="posted",
            )
        )

    if tx.buyer_user_id:
        db.add(
            Settlement(
                transaction_id=tx.id,
                user_id=tx.buyer_user_id,
                amount_pkr=tx.buyer_cost_pkr,
                fee_pkr=0.0,
                direction="debit",
                status="posted",
            )
        )

    tx.status = "settled"
    tx.verification_status = "verified"