"""Tests for image_routes.py — API integration tests."""

import json
import time

import pytest

from backend import db


class TestImageRoutes:
    """API integration tests for image CAPTCHA endpoints."""

    def test_generate_returns_required_fields(self, client):
        """POST /captcha/image/generate → 200, response has required fields."""
        resp = client.post("/captcha/image/generate")
        assert resp.status_code == 200
        data = resp.json()

        for field in [
            "challengeId",
            "token",
            "ttlMs",
            "expiresAt",
            "lines",
            "canvas",
            "instruction",
            "numIntersections",
        ]:
            assert field in data, f"Missing field: {field}"

        assert len(data["lines"]) >= 2
        assert data["numIntersections"] >= 1

    def test_generate_does_not_expose_intersections(self, client):
        """Response does NOT contain intersections (server-side only)."""
        resp = client.post("/captcha/image/generate")
        data = resp.json()

        assert "intersections" not in data
        # Also check nested
        assert "intersections" not in json.dumps(data)

    def test_validate_correct_clicks_pass(self, client):
        """POST /captcha/image/validate with valid clicks → passed=True."""
        resp = client.post("/captcha/image/generate")
        data = resp.json()
        challenge_id = data["challengeId"]

        # Fetch actual intersections from DB
        row = db.get_image_challenge(challenge_id)
        intersections = json.loads(row["intersections_json"])

        clicks = [{"x": ix[0], "y": ix[1]} for ix in intersections]

        # Wait past min solve time
        time.sleep(0.9)

        resp2 = client.post(
            "/captcha/image/validate",
            json={
                "challengeId": challenge_id,
                "token": data["token"],
                "clicks": clicks,
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["passed"] is True

    def test_validate_wrong_clicks_fail(self, client):
        """POST /captcha/image/validate with wrong clicks → passed=False."""
        resp = client.post("/captcha/image/generate")
        data = resp.json()

        # Wait past min solve time
        time.sleep(0.9)

        resp2 = client.post(
            "/captcha/image/validate",
            json={
                "challengeId": data["challengeId"],
                "token": data["token"],
                "clicks": [{"x": 1, "y": 1}],
            },
        )
        assert resp2.status_code == 200
        assert resp2.json()["passed"] is False

    def test_validate_bad_token_rejected(self, client):
        """POST /captcha/image/validate with bad token → 400."""
        resp = client.post("/captcha/image/generate")
        data = resp.json()

        resp2 = client.post(
            "/captcha/image/validate",
            json={
                "challengeId": data["challengeId"],
                "token": "bad.token",
                "clicks": [{"x": 200, "y": 200}],
            },
        )
        assert resp2.status_code == 400

    def test_validate_replay_rejected(self, client):
        """POST /captcha/image/validate twice (replay) → 410."""
        resp = client.post("/captcha/image/generate")
        data = resp.json()

        # First call
        client.post(
            "/captcha/image/validate",
            json={
                "challengeId": data["challengeId"],
                "token": data["token"],
                "clicks": [{"x": 0, "y": 0}],
            },
        )

        # Replay → 410
        resp2 = client.post(
            "/captcha/image/validate",
            json={
                "challengeId": data["challengeId"],
                "token": data["token"],
                "clicks": [{"x": 0, "y": 0}],
            },
        )
        assert resp2.status_code == 410

    def test_validate_after_ttl_expired(self, client, monkeypatch):
        """POST /captcha/image/validate after TTL → 'challenge expired'."""
        from backend import config

        monkeypatch.setattr(config, "IMAGE_CHALLENGE_TTL_MS", 0)

        resp = client.post("/captcha/image/generate")
        data = resp.json()

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
