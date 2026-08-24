from __future__ import annotations

from typing import Optional

import httpx

from app.config import settings

RESEND_URL = "https://api.resend.com/emails"


def _send(subject: str, html: str, *, to: Optional[str] = None) -> bool:
    """Send an email via Resend. Returns True on success, False on any failure
    (never raises — notification failures must not break the trading cycle)."""
    if not settings.email_enabled or not settings.resend_api_key:
        return False
    recipient = to or settings.alert_email_to
    if not recipient:
        return False
    try:
        response = httpx.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}", "Content-Type": "application/json"},
            json={"from": settings.resend_from, "to": [recipient], "subject": subject, "html": html},
            timeout=15,
        )
        return response.status_code < 300
    except Exception:
        return False


def _trade_rows(trades: list[dict]) -> str:
    if not trades:
        return "<p>No trades executed today.</p>"
    rows = "".join(
        f"<tr><td>{t.get('time', '')[:16].replace('T', ' ')}</td><td>{t.get('side')}</td>"
        f"<td>{t.get('symbol')}</td><td>{t.get('quantity')}</td><td>&#8377;{t.get('price')}</td>"
        f"<td>{t.get('reason', '')}</td></tr>"
        for t in trades
    )
    return (
        "<table cellpadding='6' style='border-collapse:collapse;width:100%'>"
        "<tr style='text-align:left;border-bottom:1px solid #ddd'>"
        "<th>Time</th><th>Side</th><th>Symbol</th><th>Qty</th><th>Price</th><th>Rationale</th></tr>"
        f"{rows}</table>"
    )


def send_daily_summary(payload: dict) -> bool:
    comparison = payload.get("comparison", {})
    portfolio = payload.get("portfolio", {})
    today_trades = payload.get("trades", [])[:20]
    subject = f"AI Trader Agent — daily summary ({comparison.get('inceptionDate', 'n/a')} -> today)"
    html = f"""
    <h2>AI Trader Agent — Daily Summary</h2>
    <p><b>Agent value:</b> &#8377;{comparison.get('agentValue')} ({comparison.get('agentReturnPct')}%)<br/>
    <b>NIFTY value:</b> &#8377;{comparison.get('niftyValue')} ({comparison.get('niftyReturnPct')}%)<br/>
    <b>Alpha:</b> {comparison.get('alphaPct')}%</p>
    <p><b>Trades today:</b> {portfolio.get('tradeCount')} total
    ({portfolio.get('buyCount')} buys / {portfolio.get('sellCount')} sells)</p>
    {_trade_rows(today_trades)}
    <p style='color:#888;font-size:12px'>Paper trading only. No real money or brokerage orders involved.</p>
    """
    return _send(subject, html)


def send_monthly_review(payload: dict, note_text: str) -> bool:
    comparison = payload.get("comparison", {})
    subject = f"AI Trader Agent — monthly review ({comparison.get('inceptionDate', 'n/a')} -> today)"
    formatted_note = note_text.replace("\n", "<br/>") if note_text else "No monthly note was generated this cycle."
    html = f"""
    <h2>AI Trader Agent — Monthly Portfolio Review</h2>
    <p><b>Agent value:</b> &#8377;{comparison.get('agentValue')} ({comparison.get('agentReturnPct')}%)<br/>
    <b>NIFTY value:</b> &#8377;{comparison.get('niftyValue')} ({comparison.get('niftyReturnPct')}%)<br/>
    <b>Alpha:</b> {comparison.get('alphaPct')}%</p>
    <div>{formatted_note}</div>
    <p style='color:#888;font-size:12px'>Paper trading only. No real money or brokerage orders involved.</p>
    """
    return _send(subject, html)


def send_alert(subject: str, detail: str) -> bool:
    return _send(f"AI Trader Agent alert: {subject}", f"<p>{detail}</p>")
