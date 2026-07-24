import pytest
from pydantic import ValidationError
from app.models import Rule


def test_overlapping_thresholds_rejected():
    with pytest.raises(ValidationError):
        Rule(
            rule_id="X",
            rule_text="x",
            success_condition="x",
            failure_condition="x",
            min_success_rate=0.8,
            max_failure_rate=0.3,
        )
