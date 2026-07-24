from app.player import route_ticket
from app.seed import initial_playbook


def test_billing_route():
    queue, rules, _ = route_ticket(
        {"subject": "Refund needed", "description": "I was charged twice"},
        initial_playbook(),
    )
    assert queue == "billing"
    assert "RULE-001" in rules


def test_trial_disambiguation():
    queue, rules, _ = route_ticket(
        {
            "subject": "Invoice API",
            "description": "Invoice API error during integration failure",
        },
        initial_playbook(),
    )
    assert queue == "technical"
    assert "RULE-004" in rules
