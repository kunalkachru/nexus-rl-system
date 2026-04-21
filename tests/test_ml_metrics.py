"""
Test suite for ML Training Metrics Dashboard and related features.

Tests:
- /training-metrics endpoint returns valid JSON
- /metrics-dashboard endpoint serves HTML
- Metrics calculations (best, avg, median, recent)
- Reward dimension breakdown calculations
- Difficulty distribution tracking
- Before/After comparison data
- Pre-event artifact loading
- Convergence analysis metrics
"""

import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient
from server.app import app


client = TestClient(app)


class TestTrainingMetricsEndpoint:
    """Test /training-metrics API endpoint."""

    def test_metrics_endpoint_exists(self):
        """Verify /training-metrics endpoint is registered."""
        response = client.get("/training-metrics")
        assert response.status_code == 200

    def test_metrics_empty_returns_valid_json(self):
        """When no episodes completed, return valid structure."""
        response = client.get("/training-metrics")
        data = response.json()

        assert data["episode_count"] >= 0
        assert isinstance(data["rewards"], list)
        assert data["best_reward"] >= 0.0
        assert data["avg_reward"] >= 0.0

    def test_metrics_required_fields(self):
        """Verify all required fields are present."""
        response = client.get("/training-metrics")
        data = response.json()

        required = [
            "episode_count", "rewards", "best_reward", "avg_reward",
            "median_reward", "recent_avg", "dimensions", "difficulty_distribution",
            "baseline", "trained"
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_metrics_dimensions_complete(self):
        """Verify all 6 reward dimensions are present."""
        response = client.get("/training-metrics")
        data = response.json()

        dimensions = ["mttr", "diagnosis", "customer", "coordination", "oversight", "depth"]
        for dim in dimensions:
            assert dim in data["dimensions"], f"Missing dimension: {dim}"
            assert isinstance(data["dimensions"][dim], list)

    def test_metrics_difficulty_distribution_complete(self):
        """Verify all difficulty levels are tracked."""
        response = client.get("/training-metrics")
        data = response.json()

        difficulties = ["easy", "medium", "hard", "very_hard", "nightmare"]
        for diff in difficulties:
            assert diff in data["difficulty_distribution"], f"Missing difficulty: {diff}"

    def test_metrics_baseline_structure(self):
        """Verify baseline (untrained) data structure."""
        response = client.get("/training-metrics")
        data = response.json()

        baseline = data["baseline"]
        assert "reward" in baseline
        assert "steps" in baseline
        # Baseline can be 0.265 (default) or loaded from artifact (~0.344)
        assert isinstance(baseline["reward"], (int, float))
        assert baseline["steps"] == 45


class TestMetricsDashboardEndpoint:
    """Test /metrics-dashboard HTML endpoint."""

    def test_dashboard_endpoint_exists(self):
        """Verify /metrics-dashboard endpoint is registered."""
        response = client.get("/metrics-dashboard")
        assert response.status_code == 200

    def test_dashboard_returns_html(self):
        """Verify dashboard returns valid HTML."""
        response = client.get("/metrics-dashboard")
        assert "text/html" in response.headers["content-type"]

    def test_dashboard_contains_required_elements(self):
        """Verify dashboard HTML contains all required sections."""
        response = client.get("/metrics-dashboard")
        html = response.text

        required = [
            "NEXUS Training Metrics",
            "overview", "dimensions", "curriculum", "convergence", "comparison",
            "chartRewardCurve", "chartMTTR",
        ]
        for elem in required:
            assert elem in html, f"Missing element: {elem}"

    def test_dashboard_contains_chart_library(self):
        """Verify dashboard loads Chart.js library."""
        response = client.get("/metrics-dashboard")
        html = response.text
        assert "chart.js" in html.lower() or "Chart" in html


class TestMetricsCalculations:
    """Test reward calculations and statistics."""

    def test_best_reward_is_valid(self):
        """Verify best reward is a valid number."""
        response = client.get("/training-metrics")
        data = response.json()
        assert isinstance(data["best_reward"], (int, float))
        assert data["best_reward"] >= 0.0

    def test_average_reward_calculation(self):
        """Verify average reward calculation."""
        response = client.get("/training-metrics")
        data = response.json()

        if data["episode_count"] > 0:
            expected_avg = sum(data["rewards"]) / len(data["rewards"])
            assert abs(data["avg_reward"] - expected_avg) < 0.001

    def test_median_reward_calculation(self):
        """Verify median reward is calculated correctly."""
        response = client.get("/training-metrics")
        data = response.json()

        if data["episode_count"] > 0:
            sorted_rewards = sorted(data["rewards"])
            expected_median = sorted_rewards[len(sorted_rewards) // 2]
            assert abs(data["median_reward"] - expected_median) < 0.001

    def test_recent_average_calculation(self):
        """Verify recent average (last 5 episodes) is correct."""
        response = client.get("/training-metrics")
        data = response.json()

        if data["episode_count"] > 0:
            recent_5 = data["rewards"][-5:]
            expected_recent = sum(recent_5) / min(5, len(recent_5))
            assert abs(data["recent_avg"] - expected_recent) < 0.001


class TestRewardDimensions:
    """Test reward dimension tracking."""

    def test_all_dimensions_present_when_episodes_exist(self):
        """Verify all 6 dimensions are present with correct proportions."""
        response = client.get("/training-metrics")
        data = response.json()

        dims = data["dimensions"]
        for dim_name, dim_data in dims.items():
            assert isinstance(dim_data, list), f"{dim_name} should be a list"
            # Each dimension should have data for all episodes
            assert len(dim_data) == data["episode_count"]

    def test_dimension_proportions(self):
        """Verify dimension proportions sum correctly."""
        response = client.get("/training-metrics")
        data = response.json()

        if data["episode_count"] > 0:
            # Total of all dimensions should equal avg reward
            for i in range(min(5, data["episode_count"])):  # Check first 5
                total = sum(
                    data["dimensions"][dim][i]
                    for dim in ["mttr", "diagnosis", "customer", "coordination", "oversight", "depth"]
                )
                # Should be approximately equal to reward (±rounding error)
                assert abs(total - data["rewards"][i]) < 0.01


class TestDifficultyDistribution:
    """Test curriculum learning tracking."""

    def test_difficulty_distribution_sums_correctly(self):
        """Verify difficulty counts are all non-negative."""
        response = client.get("/training-metrics")
        data = response.json()

        diff_dist = data["difficulty_distribution"]
        for diff_level, count in diff_dist.items():
            assert count >= 0, f"Negative count for {diff_level}"

    def test_difficulty_progression_logical(self):
        """Verify difficulty progression makes sense."""
        response = client.get("/training-metrics")
        data = response.json()

        diff_dist = data["difficulty_distribution"]
        # All values should be non-negative
        for level, count in diff_dist.items():
            assert isinstance(count, int)
            assert count >= 0


class TestBeforeAfterComparison:
    """Test before/after training comparison data."""

    def test_baseline_and_trained_structure(self):
        """Verify baseline and trained structures are present."""
        response = client.get("/training-metrics")
        data = response.json()

        assert "baseline" in data
        assert "trained" in data
        assert isinstance(data["baseline"], dict)
        assert isinstance(data["trained"], dict)

    def test_baseline_performance_values(self):
        """Verify baseline data contains expected fields."""
        response = client.get("/training-metrics")
        data = response.json()

        baseline = data["baseline"]
        assert "reward" in baseline
        assert "steps" in baseline
        assert baseline["reward"] > 0
        assert baseline["steps"] > 0

    def test_trained_performance_values(self):
        """Verify trained data contains expected fields."""
        response = client.get("/training-metrics")
        data = response.json()

        trained = data["trained"]
        assert "reward" in trained
        assert "steps" in trained
        assert trained["reward"] >= 0
        assert trained["steps"] > 0


class TestPreEventArtifactLoading:
    """Test loading of pre-event training artifacts."""

    def test_pre_event_artifacts_exist(self):
        """Verify pre-event training artifact files exist."""
        base_path = Path(__file__).parent.parent / "training_artifacts"

        artifact_files = [
            base_path / "pre_event_reward_curves.json",
            base_path / "pre_event_benchmark.json",
            base_path / "reward_curve.png"
        ]

        for artifact_file in artifact_files:
            assert artifact_file.exists(), f"Missing artifact: {artifact_file.name}"

    def test_reward_curves_json_is_list(self):
        """Verify pre-event reward curves JSON is a valid list."""
        artifact_path = (
            Path(__file__).parent.parent / "training_artifacts" / "pre_event_reward_curves.json"
        )

        if artifact_path.exists():
            with open(artifact_path) as f:
                data = json.load(f)

            assert isinstance(data, list)
            assert len(data) > 0
            # Each item should have a reward field
            for item in data[:5]:  # Check first 5
                assert "reward" in item

    def test_benchmark_json_has_reward_metric(self):
        """Verify pre-event benchmark JSON has reward metrics."""
        artifact_path = (
            Path(__file__).parent.parent / "training_artifacts" / "pre_event_benchmark.json"
        )

        if artifact_path.exists():
            with open(artifact_path) as f:
                data = json.load(f)

            assert isinstance(data, dict)
            # Should have some form of reward metric
            reward_fields = ["reward", "avg_reward", "reward_score", "score"]
            assert any(field in data for field in reward_fields), \
                f"No reward field found in benchmark"


class TestMetricsDataTypes:
    """Test correct data types in metrics response."""

    def test_all_numeric_values_are_floats(self):
        """Verify all numeric metrics are floats."""
        response = client.get("/training-metrics")
        data = response.json()

        numeric_fields = ["best_reward", "avg_reward", "median_reward", "recent_avg"]
        for field in numeric_fields:
            value = data[field]
            assert isinstance(value, (int, float)), f"{field} should be numeric"

    def test_rewards_array_contains_floats(self):
        """Verify rewards array contains float values."""
        response = client.get("/training-metrics")
        data = response.json()

        for reward in data["rewards"]:
            assert isinstance(reward, (int, float))

    def test_difficulty_distribution_contains_integers(self):
        """Verify difficulty counts are integers."""
        response = client.get("/training-metrics")
        data = response.json()

        for difficulty, count in data["difficulty_distribution"].items():
            assert isinstance(count, int)


class TestMetricsDataConsistency:
    """Test consistency of metrics data."""

    def test_rewards_length_matches_episode_count(self):
        """Verify rewards array length equals episode count."""
        response = client.get("/training-metrics")
        data = response.json()

        assert len(data["rewards"]) == data["episode_count"]

    def test_dimension_arrays_match_rewards_length(self):
        """Verify each dimension array matches rewards length."""
        response = client.get("/training-metrics")
        data = response.json()

        for dim_name, dim_data in data["dimensions"].items():
            assert len(dim_data) == data["episode_count"], \
                f"Dimension {dim_name} length mismatch"

    def test_best_reward_is_maximum(self):
        """Verify best reward is actually the maximum reward."""
        response = client.get("/training-metrics")
        data = response.json()

        if data["rewards"]:
            assert data["best_reward"] >= max(data["rewards"]) - 0.001


def test_integration_scenario():
    """End-to-end integration test of metrics system."""
    # 1. Check metrics endpoint exists
    response = client.get("/training-metrics")
    assert response.status_code == 200
    metrics = response.json()

    # 2. Verify data structure
    assert "episode_count" in metrics
    assert "rewards" in metrics
    assert "dimensions" in metrics
    assert "difficulty_distribution" in metrics

    # 3. Check dashboard can load
    dashboard_resp = client.get("/metrics-dashboard")
    assert dashboard_resp.status_code == 200
    assert "NEXUS" in dashboard_resp.text

    # 4. Verify metrics API is callable from dashboard
    assert "/training-metrics" in dashboard_resp.text or \
           "training-metrics" in dashboard_resp.text


def test_metrics_endpoint_performance():
    """Test that metrics endpoint responds quickly."""
    import time
    start = time.time()
    response = client.get("/training-metrics")
    elapsed = time.time() - start

    assert response.status_code == 200
    # Should respond in < 100ms
    assert elapsed < 0.1, f"Metrics endpoint took {elapsed:.3f}s (too slow)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
