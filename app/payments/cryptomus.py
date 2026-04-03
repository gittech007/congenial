from __future__ import annotations

import hashlib
import json
import logging
from base64 import b64encode

import httpx

from config import settings

logger = logging.getLogger(__name__)

CRYPTOMUS_API_URL = "https://api.cryptomus.com/v1"


def _make_sign(payload: dict) -> str:
    """Generate Cryptomus request signature."""
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    body_b64 = b64encode(body.encode("utf-8")).decode("utf-8")
    raw = body_b64 + settings.cryptomus_api_key
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


async def create_invoice(
    order_id: int,
    amount_usd: float,
) -> dict:
    """Create a Cryptomus payment invoice.

    Returns the full Cryptomus API response dict on success.
    Raises httpx.HTTPStatusError or ValueError on failure.
    """
    payload = {
        "order_id": str(order_id),
        "amount": f"{amount_usd:.2f}",
        "currency": "USD",
        "url_callback": f"https://{settings.app_domain}/payments/cryptomus/webhook",
        "lifetime": 7200,
    }
    sign = _make_sign(payload)

    headers = {
        "merchant": settings.cryptomus_merchant_id,
        "sign": sign,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{CRYPTOMUS_API_URL}/payment",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()

    if data.get("state") != 0:
        raise ValueError(f"Cryptomus error: {data.get('message', 'Unknown error')}")

    return data.get("result", data)
