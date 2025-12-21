import base64
import hmac
import json
from typing import Any, Dict

from . import config


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def sign(payload: Dict[str, Any]) -> str:
    msg = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(config.SECRET_KEY.encode(), msg, digestmod="sha256").digest()
    return f"{_b64encode(msg)}.{_b64encode(sig)}"


def verify(token: str) -> Dict[str, Any]:
    try:
        msg_b64, sig_b64 = token.split(".")
    except ValueError:
        raise ValueError("invalid token format")
    msg = _b64decode(msg_b64)
    expected = hmac.new(config.SECRET_KEY.encode(), msg, digestmod="sha256").digest()
    actual = _b64decode(sig_b64)
    if not hmac.compare_digest(expected, actual):
        raise ValueError("invalid signature")
    return json.loads(msg.decode())
