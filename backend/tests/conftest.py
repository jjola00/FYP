"""Shared fixtures for backend tests."""

import os
import sys

import pytest

# Ensure backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def _tmp_db(tmp_path, monkeypatch):
    """Point the database to a temporary directory for each test."""
    from backend import config

    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "captcha.db")

    from backend import db

    db.init_db()
    yield


@pytest.fixture()
def client():
    """FastAPI TestClient for integration tests."""
    from backend.main import app
    from fastapi.testclient import TestClient

    return TestClient(app)
