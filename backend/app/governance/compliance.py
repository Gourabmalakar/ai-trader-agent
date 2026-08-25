from __future__ import annotations

from dataclasses import asdict, dataclass

from app.config import settings
from app.models import OrderStatus
from app.portfolio.ledger import PortfolioLedger
from app.scheduler.calendar import is_market_open

RULES_CHECKED = [
    "Every filled trade occurs only inside the 09:15-15:30 IST NSE trading window",
    "Trade notional always equals price x quantity (no fabricated or edited fills)",
    "Portfolio cash balance never goes negative across recorded snapshots",
    "No single holding exceeds the configured max single-stock weight right now",
]


@dataclass
class ComplianceViolation:
    subject: str
    timestamp: str
    rule: str
    detail: str


class GovernanceOfficer:
    """Independent, deterministic re-check of the executed trade log against the fund's own
    stated risk rules, run fresh every dashboard build.

    This is a *detective* control, distinct from RiskManager (which is *preventive* and runs
    before a trade is ever filled): it exists so a public visitor doesn't have to take the
    trading desk's word for it — every fill and every snapshot is independently re-verified
    after the fact against the same rules the fund claims to follow. It has no ability to
    reverse or alter trades; it only reports what it finds.
    """

    def audit(self, ledger: PortfolioLedger, latest_prices: dict[str, float], total_value: float) -> dict:
        violations: list[ComplianceViolation] = []
        filled = [trade for trade in ledger.trades if trade.status == OrderStatus.FILLED_PAPER]

        for trade in filled:
            if not is_market_open(trade.timestamp):
                violations.append(
                    ComplianceViolation(
                        trade.symbol,
                        trade.timestamp.isoformat(),
                        "trading_window",
                        f"{trade.side.value} {trade.quantity} {trade.symbol} filled outside the 09:15-15:30 IST session.",
                    )
                )
            # notional is computed from the unrounded fill price at execution time, while
            # trade.price is that same fill price rounded to paise — so a few-paisa-per-share
            # gap between price*quantity and the recorded notional is expected rounding, not a
            # bookkeeping error. Scale the tolerance with quantity so real fills never false-
            # positive here while a genuinely fabricated notional still gets caught.
            expected_notional = round(trade.price * trade.quantity, 2)
            tolerance = max(0.5, 0.01 * trade.quantity)
            if abs(expected_notional - round(trade.notional, 2)) > tolerance:
                violations.append(
                    ComplianceViolation(
                        trade.symbol,
                        trade.timestamp.isoformat(),
                        "bookkeeping",
                        f"Recorded notional {trade.notional} does not match price x quantity ({expected_notional}).",
                    )
                )
            if trade.quantity <= 0 or trade.price <= 0:
                violations.append(
                    ComplianceViolation(
                        trade.symbol,
                        trade.timestamp.isoformat(),
                        "invalid_fill",
                        f"Non-positive quantity or price on a FILLED_PAPER trade ({trade.quantity} @ {trade.price}).",
                    )
                )

        for snapshot in ledger.snapshots:
            if snapshot.get("cash", 0) < -0.01:
                violations.append(
                    ComplianceViolation(
                        "PORTFOLIO",
                        snapshot.get("timestamp", ""),
                        "cash_buffer",
                        f"Cash balance went negative: {snapshot.get('cash')}.",
                    )
                )

        if total_value:
            for symbol, position in ledger.positions.items():
                price = latest_prices.get(symbol, position.average_price)
                weight = (position.quantity * price) / total_value
                if weight > settings.max_position_weight + 0.005:  # small tolerance for rounding
                    violations.append(
                        ComplianceViolation(
                            symbol,
                            "current",
                            "position_limit",
                            f"Current weight {weight:.1%} exceeds the {settings.max_position_weight:.0%} single-stock cap.",
                        )
                    )

        return {
            "auditedTrades": len(filled),
            "auditedSnapshots": len(ledger.snapshots),
            "violations": [asdict(v) for v in violations],
            "status": "CLEAN" if not violations else "VIOLATIONS_FOUND",
            "rulesChecked": RULES_CHECKED,
        }
