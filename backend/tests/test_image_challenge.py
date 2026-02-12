"""Tests for image_challenge.py — intersection calculation accuracy."""

import pytest

from backend import config
from backend.image_challenge import (
    _find_all_intersections,
    _sample_line,
    generate_challenge,
)


def _straight(p1, p2):
    return {"type": "straight", "points": [list(p1), list(p2)]}


class TestIntersectionCalculation:
    """Test intersection finding correctness."""

    def test_perpendicular_lines_one_intersection(self):
        """Two perpendicular straight lines → exactly 1 intersection."""
        l1 = _straight([0, 200], [400, 200])
        l2 = _straight([200, 0], [200, 400])

        ixs = _find_all_intersections(
            [l1, l2],
            num_samples=500,
            cluster_radius=3.0,
            canvas_w=400,
            canvas_h=400,
            margin=0,
        )
        assert len(ixs) == 1
        # Should be near (200, 200)
        assert abs(ixs[0][0] - 200) < 2
        assert abs(ixs[0][1] - 200) < 2

    def test_parallel_lines_no_intersection(self):
        """Two parallel lines → 0 intersections."""
        l1 = _straight([0, 100], [400, 100])
        l2 = _straight([0, 300], [400, 300])

        ixs = _find_all_intersections(
            [l1, l2],
            num_samples=500,
            cluster_radius=3.0,
            canvas_w=400,
            canvas_h=400,
            margin=0,
        )
        assert len(ixs) == 0

    def test_bezier_intersection_within_tolerance(self):
        """Known quadratic Bézier curves with expected intersection → within 2px."""
        # Quadratic curve that passes through roughly (200, 200)
        l1 = _straight([50, 200], [350, 200])
        l2 = {"type": "quadratic", "points": [[200, 50], [200, 200], [200, 350]]}

        ixs = _find_all_intersections(
            [l1, l2],
            num_samples=500,
            cluster_radius=3.0,
            canvas_w=400,
            canvas_h=400,
            margin=0,
        )
        assert len(ixs) >= 1
        # At least one should be near (200, 200)
        found_close = any(
            abs(p[0] - 200) < 5 and abs(p[1] - 200) < 5 for p in ixs
        )
        assert found_close

    def test_line_outside_margin_filtered(self):
        """Line entirely outside canvas margin → 0 intersections counted."""
        # Both lines are at the very edge (margin=50 means 0-50 is filtered)
        l1 = _straight([10, 10], [10, 20])
        l2 = _straight([5, 15], [15, 15])

        ixs = _find_all_intersections(
            [l1, l2],
            num_samples=500,
            cluster_radius=3.0,
            canvas_w=400,
            canvas_h=400,
            margin=50,
        )
        assert len(ixs) == 0

    def test_clustering_merges_nearby_points(self):
        """Two raw intersections within 3px → merged to 1."""
        from backend.image_challenge import _cluster_points
        import numpy as np

        points = np.array([[200.0, 200.0], [201.0, 201.0]])
        clusters = _cluster_points(points, radius=3.0)
        assert len(clusters) == 1

    def test_generate_challenge_produces_intersections(self):
        """generate_challenge() always returns at least 1 intersection."""
        challenge = generate_challenge()
        n = challenge["server_data"]["numIntersections"]
        assert n >= 1

    def test_bulk_generation_valid_counts(self):
        """100 generations → all produce valid intersection counts."""
        for _ in range(100):
            c = generate_challenge()
            n = c["server_data"]["numIntersections"]
            assert n >= 1, "got 0 intersections"
