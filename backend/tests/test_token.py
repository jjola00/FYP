"""Tests for captcha_token.py — sign/verify, tamper, malformed, reuse, expiry."""

import time

import pytest

from backend import captcha_token, db


class TestToken:
    """Token signing and verification tests."""

    def test_sign_verify_roundtrip(self):
        """sign() → verify() round-trip succeeds."""
        payload = {"cid": "abc123", "type": "image", "iat": time.time()}
        token = captcha_token.sign(payload)
        result = captcha_token.verify(token)
        assert result["cid"] == "abc123"
        assert result["type"] == "image"

    def test_tampered_token_rejected(self):
        """Tampered token → verify() raises ValueError."""
        payload = {"cid": "abc123", "type": "image"}
        token = captcha_token.sign(payload)
        # Flip a character in the signature
        parts = token.split(".")
        tampered_sig = parts[1][:-1] + ("a" if parts[1][-1] != "a" else "b")
        tampered_token = f"{parts[0]}.{tampered_sig}"
        with pytest.raises(ValueError):
            captcha_token.verify(tampered_token)

    def test_malformed_token_rejected(self):
        """Malformed token (no dot) → verify() raises ValueError."""
        with pytest.raises(ValueError):
            captcha_token.verify("nodothere")

    def test_token_reuse_rejected(self, client):
        """Token reuse: validate once → passes; validate again → HTTP 410."""
        # Generate a challenge
        resp = client.post("/captcha/image/generate")
        assert resp.status_code == 200
        data = resp.json()

        challenge_id = data["challengeId"]
        token = data["token"]

        # First validate (with wrong clicks, just to consume it)
        resp1 = client.post(
            "/captcha/image/validate",
            json={
                "challengeId": challenge_id,
                "token": token,
                "clicks": [{"x": 0, "y": 0}],
            },
        )
        assert resp1.status_code == 200

        # Second validate → 410
        resp2 = client.post(
            "/captcha/image/validate",
            json={
                "challengeId": challenge_id,
                "token": token,
                "clicks": [{"x": 0, "y": 0}],
            },
        )
        assert resp2.status_code == 410

    def test_expired_challenge(self, client, monkeypatch):
        """Expired challenge → validate returns 'challenge expired'."""
        from backend import config

        # Set TTL to 0ms so it expires immediately
        monkeypatch.setattr(config, "IMAGE_CHALLENGE_TTL_MS", 0)

        resp = client.post("/captcha/image/generate")
        data = resp.json()

        # Wait a moment for expiry
        time.sleep(0.01)

        resp2 = client.post(
            "/captcha/image/validate",
            json={
                "challengeId": data["challengeId"],
                "token": data["token"],
                "clicks": [{"x": 200, "y": 200}],
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["reason"] == "challenge expired"
