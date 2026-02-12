"""Tests for image_validator.py — tolerance and edge cases."""

import pytest

from backend import config
from backend.image_validator import validate_clicks


# Standard intersection at (200, 200) for testing
INTERSECTIONS = [[200.0, 200.0]]


class TestValidateClicks:
    """Test click validation logic."""

    def test_click_exactly_on_intersection(self):
        """Click exactly on intersection → pass."""
        result = validate_clicks(
            clicks=[{"x": 200, "y": 200}],
            intersections=INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is True

    def test_click_at_tolerance_boundary(self):
        """Click at tolerance boundary (15px away) → pass."""
        tol = config.IMAGE_CLICK_TOLERANCE_PX  # 15
        result = validate_clicks(
            clicks=[{"x": 200 + tol, "y": 200}],
            intersections=INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is True

    def test_click_beyond_tolerance(self):
        """Click at 16px away → fail (missed)."""
        result = validate_clicks(
            clicks=[{"x": 216, "y": 200}],
            intersections=INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is False
        assert "missed" in result["reason"]

    def test_correct_plus_one_stray_fails(self):
        """All intersections clicked + 1 stray click in empty space → fail."""
        result = validate_clicks(
            clicks=[{"x": 200, "y": 200}, {"x": 50, "y": 50}],
            intersections=INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is False
        assert "extra" in result["reason"]

    def test_correct_plus_two_stray_fails(self):
        """All intersections clicked + 2 stray clicks → fail."""
        result = validate_clicks(
            clicks=[
                {"x": 200, "y": 200},
                {"x": 50, "y": 50},
                {"x": 60, "y": 60},
            ],
            intersections=INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is False
        assert "extra" in result["reason"]

    def test_duplicate_click_on_same_intersection_passes(self):
        """Clicking the same intersection twice → pass (duplicate is fine)."""
        result = validate_clicks(
            clicks=[{"x": 200, "y": 200}, {"x": 201, "y": 199}],
            intersections=INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is True

    def test_solve_too_fast(self):
        """Solve time 500ms → fail (too fast, threshold is 800ms)."""
        result = validate_clicks(
            clicks=[{"x": 200, "y": 200}],
            intersections=INTERSECTIONS,
            solve_time_ms=500,
        )
        assert result["passed"] is False
        assert result["too_fast"] is True

    def test_solve_at_threshold(self):
        """Solve time 800ms → pass."""
        result = validate_clicks(
            clicks=[{"x": 200, "y": 200}],
            intersections=INTERSECTIONS,
            solve_time_ms=800,
        )
        assert result["passed"] is True

    def test_solve_above_threshold(self):
        """Solve time 801ms → pass."""
        result = validate_clicks(
            clicks=[{"x": 200, "y": 200}],
            intersections=INTERSECTIONS,
            solve_time_ms=801,
        )
        assert result["passed"] is True

    def test_zero_clicks_fail(self):
        """0 clicks submitted → fail."""
        result = validate_clicks(
            clicks=[],
            intersections=INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is False

    def test_min_solve_disabled(self, monkeypatch):
        """ENFORCE_IMAGE_MIN_SOLVE=False → fast solve still passes."""
        monkeypatch.setattr(config, "ENFORCE_IMAGE_MIN_SOLVE", False)
        result = validate_clicks(
            clicks=[{"x": 200, "y": 200}],
            intersections=INTERSECTIONS,
            solve_time_ms=100,
        )
        assert result["passed"] is True


# ─── Multi-intersection stray-click tests ────────────────────────────────

TWO_INTERSECTIONS = [[100.0, 100.0], [300.0, 300.0]]


class TestStrayClickRejection:
    """Verify that every click must be near an intersection."""

    def test_two_correct_clicks_pass(self):
        """2 intersections, 2 correct clicks → pass."""
        result = validate_clicks(
            clicks=[{"x": 100, "y": 100}, {"x": 300, "y": 300}],
            intersections=TWO_INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is True

    def test_two_correct_plus_one_random_fails(self):
        """2 intersections, 2 correct + 1 random click → fail."""
        result = validate_clicks(
            clicks=[
                {"x": 100, "y": 100},
                {"x": 300, "y": 300},
                {"x": 50, "y": 50},
            ],
            intersections=TWO_INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is False
        assert "extra" in result["reason"]

    def test_two_correct_plus_duplicate_passes(self):
        """2 intersections, 2 correct + 1 duplicate near existing → pass."""
        result = validate_clicks(
            clicks=[
                {"x": 100, "y": 100},
                {"x": 300, "y": 300},
                {"x": 102, "y": 98},  # near first intersection
            ],
            intersections=TWO_INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is True

    def test_one_correct_plus_one_random_fails(self):
        """2 intersections, 1 correct + 1 random → fail."""
        result = validate_clicks(
            clicks=[{"x": 100, "y": 100}, {"x": 50, "y": 50}],
            intersections=TWO_INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is False

    def test_three_correct_one_duplicate_passes(self):
        """2 intersections, 3 clicks (one is duplicate) → pass."""
        result = validate_clicks(
            clicks=[
                {"x": 100, "y": 100},
                {"x": 300, "y": 300},
                {"x": 299, "y": 301},  # duplicate near second
            ],
            intersections=TWO_INTERSECTIONS,
            solve_time_ms=5000,
        )
        assert result["passed"] is True
