"""Tests for incident library — all cases load with valid required fields."""

import pytest
from server.incidents import INCIDENT_LIBRARY, get_incident, get_incidents_by_difficulty
from server.data_models import IncidentCase, Severity


ALL_CASE_IDS = [
    "INC001",
    "INC002",
    "INC003",
    "INC004",
    "INC005",
    "INC006",
    "INC007",
    "INC008",
]


class TestIncidentLibrary:
    def test_all_incidents_present(self):
        assert set(INCIDENT_LIBRARY.keys()) == set(ALL_CASE_IDS)

    def test_get_incident_returns_correct_type(self):
        inc = get_incident("INC001")
        assert isinstance(inc, IncidentCase)

    def test_get_incident_unknown_raises(self):
        with pytest.raises((ValueError, KeyError)):
            get_incident("INC999")

    def test_get_incidents_by_difficulty_easy(self):
        easy = get_incidents_by_difficulty("easy")
        assert len(easy) >= 1
        assert all(i.difficulty == "easy" for i in easy)

    def test_get_incidents_by_difficulty_unknown_empty(self):
        result = get_incidents_by_difficulty("legendary")
        assert result == []

    def test_incident_ids_match_library_keys(self):
        for key, inc in INCIDENT_LIBRARY.items():
            assert inc.case_id == key

    def test_all_incidents_have_required_fields(self):
        required = [
            "case_id", "title", "severity", "difficulty",
            "initial_alerts", "customer_reports", "affected_services",
            "affected_regions", "root_cause", "correct_mitigation_steps",
            "available_runbooks", "optimal_mttr_minutes", "max_steps",
        ]
        for case_id in ALL_CASE_IDS:
            inc = get_incident(case_id)
            for field in required:
                val = getattr(inc, field, None)
                assert val is not None, f"{case_id} missing {field}"
                if isinstance(val, list):
                    assert len(val) > 0, f"{case_id}.{field} is empty list"


class TestIncidentContent:
    def test_inc008_is_theme_32_personal_easy(self):
        inc = get_incident("INC008")
        assert inc.difficulty == "easy"
        from server.data_models import IncidentType

        assert inc.incident_type == IncidentType.PERSONAL_ASSISTANT

    def test_inc001_is_easy_p1(self):
        inc = get_incident("INC001")
        assert inc.difficulty == "easy"
        assert inc.severity == Severity.P1

    def test_inc003_has_competing_hypotheses(self):
        inc = get_incident("INC003")
        assert len(inc.competing_hypotheses) >= 2, "INC003 (medium) must have coalition debate"

    def test_inc003_correct_hypothesis_keywords(self):
        inc = get_incident("INC003")
        assert len(inc.correct_hypothesis_keywords) >= 3

    def test_inc007_is_nightmare(self):
        inc = get_incident("INC007")
        assert inc.difficulty in ("nightmare", "very_hard")

    def test_inc007_has_schema_drift_step(self):
        inc = get_incident("INC007")
        assert inc.schema_drift_step is not None
        assert 15 <= inc.schema_drift_step <= 25

    def test_non_nightmare_no_schema_drift(self):
        for case_id in ALL_CASE_IDS:
            if case_id == "INC007":
                continue
            inc = get_incident(case_id)
            assert inc.schema_drift_step is None, f"{case_id} should not have schema drift"

    def test_runbooks_have_at_least_one_correct_step(self):
        for case_id in ALL_CASE_IDS:
            inc = get_incident(case_id)
            correct = [s for s in inc.available_runbooks if s.is_correct_step]
            assert len(correct) >= 1, f"{case_id} has no correct runbook steps"

    def test_red_herrings_present_in_non_easy(self):
        # Medium+ incidents must have at least one red herring to test discrimination
        for case_id in ["INC003", "INC004", "INC005"]:
            inc = get_incident(case_id)
            rh = [a for a in inc.initial_alerts if a.is_red_herring]
            assert len(rh) >= 1, f"{case_id} should have red herring alerts"

    def test_blast_radius_has_users_affected(self):
        for case_id in ALL_CASE_IDS:
            inc = get_incident(case_id)
            assert "users_affected" in inc.blast_radius
            assert inc.blast_radius["users_affected"] > 0

    def test_optimal_mttr_less_than_baseline(self):
        for case_id in ALL_CASE_IDS:
            inc = get_incident(case_id)
            assert inc.optimal_mttr_minutes < inc.baseline_mttr_minutes, \
                f"{case_id}: optimal >= baseline"

    def test_max_steps_positive(self):
        for case_id in ALL_CASE_IDS:
            inc = get_incident(case_id)
            assert inc.max_steps >= 10

    def test_difficulty_progression(self):
        difficulties = {i.difficulty for i in INCIDENT_LIBRARY.values()}
        assert "easy" in difficulties
        assert "medium" in difficulties
        # Hard or harder must exist
        assert difficulties & {"hard", "very_hard", "nightmare"}
