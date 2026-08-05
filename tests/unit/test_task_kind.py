import pytest

from foreman_ai_hq.task_kind import (
    CANONICAL_TASK_KINDS,
    DEFAULT_TASK_KIND,
    read_task_kind,
    validate_task_kind,
    with_task_kind,
)


class TestReadTaskKind:
    def test_prefers_task_kind(self):
        assert read_task_kind({"task_kind": "acceptance_verification"}) == "acceptance_verification"
        assert read_task_kind({"task_kind": "implementation"}) == "implementation"

    def test_legacy_scout_is_tolerated(self):
        assert read_task_kind({"task_kind": "scout"}) == "scout"
        assert read_task_kind({"task_breakdown_kind": "scout"}) == "scout"

    def test_falls_back_to_legacy_task_breakdown_kind(self):
        assert read_task_kind({"task_breakdown_kind": "acceptance_verification"}) == "acceptance_verification"
        assert read_task_kind({"task_breakdown_kind": "implementation"}) == "implementation"

    def test_prefers_task_kind_over_legacy(self):
        assert read_task_kind({"task_kind": "implementation", "task_breakdown_kind": "scout"}) == "implementation"

    def test_defaults_unknown_or_missing_to_implementation(self):
        assert read_task_kind({}) == DEFAULT_TASK_KIND
        assert read_task_kind({"task_kind": "research"}) == DEFAULT_TASK_KIND
        assert read_task_kind({"task_breakdown_kind": 123}) == DEFAULT_TASK_KIND
        assert read_task_kind(None) == DEFAULT_TASK_KIND


class TestValidateTaskKind:
    def test_accepts_canonical_kinds(self):
        assert validate_task_kind("implementation") == "implementation"
        assert validate_task_kind("acceptance_verification") == "acceptance_verification"

    def test_rejects_invalid_kinds(self):
        with pytest.raises(ValueError, match="task_kind must be one of"):
            validate_task_kind("scout")
        with pytest.raises(ValueError, match="task_kind must be one of"):
            validate_task_kind("research")
        with pytest.raises(ValueError, match="task_kind must be one of"):
            validate_task_kind(123)


class TestWithTaskKind:
    def test_sets_canonical_kind(self):
        assert with_task_kind({}, "implementation") == {"task_kind": "implementation"}

    def test_preserves_other_metadata(self):
        assert with_task_kind({"project_id": "p1"}, "acceptance_verification") == {
            "project_id": "p1",
            "task_kind": "acceptance_verification",
        }

    def test_rejects_invalid_kind(self):
        with pytest.raises(ValueError, match="task_kind must be one of"):
            with_task_kind({}, "research")
        with pytest.raises(ValueError, match="task_kind must be one of"):
            with_task_kind({}, "scout")
