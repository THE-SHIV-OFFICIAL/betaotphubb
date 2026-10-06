#MADE_BY_NOBITA
"""BETA BOT HUB payment gateway (auto-verified UPI).

Docs: https://betapaymentgateway.up.railway.app/#docs
  POST /api/v1/payments/create   -> create order (QR + pay link)
  GET  /api/v1/payments/<id>     -> {"verified": bool, "order": {"status": PENDING|PAID|EXPIRED}}
"""
import os
import aiohttp

PAYGATE_URL = os.getenv("PAYGATE_URL", "https://betapaymentgateway.up.railway.app").rstrip("/")


def _key() -> str:
    """Admin setting > PAYGATE_API_KEY environment secret; never fall back to a source-code key."""
    try:
        from database import cur
        row = cur.execute("SELECT value FROM settings WHERE key='paygate_key'").fetchone()
        if row and row[0]: return row[0].strip()
    except Exception:
        pass
    return (os.getenv("PAYGATE_API_KEY") or "").strip()

PAYGATE_API_KEY = _key()

_TIMEOUT = aiohttp.ClientTimeout(total=20)


_session = None


def get_http_session() -> aiohttp.ClientSession:
    """One shared keep-alive session (no socket leak, faster requests)."""
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(limit=100, keepalive_timeout=60), timeout=_TIMEOUT)
    return _session


async def close_http_session():
    global _session
    if _session is not None and not _session.closed:
        await _session.close()
    _session = None


class PayGateError(Exception):
    pass


def _headers():
    k = _key()
    if not k:
        raise PayGateError("PAYGATE_API_KEY is not set")
    return {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}


def is_enabled() -> bool:
    return bool(_key())


async def create_payment(amount: int, note: str = "", customer_email: str = "") -> dict:
    """Returns the order dict: orderId, payAmount, qrImageUrl, upiUri, payUrl, expiresAt ..."""
    body = {"amount": amount, "note": note}
    if customer_email:
        body["customerEmail"] = customer_email
    s = get_http_session()
    async with s.post(f"{PAYGATE_URL}/api/v1/payments/create", json=body, headers=_headers()) as r:
        data = await r.json(content_type=None)
    if not data.get("success") or not data.get("order", {}).get("orderId"):
        raise PayGateError(str(data.get("error") or data.get("message") or data))
    return data["order"]


async def get_status(order_id: str) -> tuple[str, bool, dict]:
    """Returns (status, verified, order)."""
    s = get_http_session()
    async with s.get(f"{PAYGATE_URL}/api/v1/payments/{order_id}", headers=_headers()) as r:
        data = await r.json(content_type=None)
    order = data.get("order") or {}
    return str(order.get("status", "PENDING")).upper(), bool(data.get("verified")), order
