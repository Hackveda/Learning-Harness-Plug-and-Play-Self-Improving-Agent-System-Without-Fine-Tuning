from __future__ import annotations

from app.models import FixedReference, Playbook, Rule
from app.storage import get_champion, init_db, save_playbook


def initial_playbook() -> Playbook:
    return Playbook(
        version="1.0.0",
        champion_score=0.70,
        fixed_reference_data=[
            FixedReference(
                key="allowed_queues",
                value=["billing", "technical", "account", "general"],
                description="Approved support routing queues.",
            ),
            FixedReference(
                key="urgent_terms",
                value=["urgent", "blocked", "payment failed", "security"],
                description="Terms that may justify priority handling.",
            ),
            FixedReference(
                key="pii_policy",
                value="Never persist full payment-card numbers or passwords.",
                description="Immutable logging restriction.",
            ),
        ],
        proven_rules=[
            Rule(
                rule_id="RULE-001",
                rule_text="Route refund, invoice and payment issues to billing.",
                success_condition="The true queue is billing.",
                failure_condition="The true queue is not billing.",
                evaluation_window=20,
                status="confirmed",
                min_success_rate=0.80,
                max_failure_rate=0.20,
                created_by="seed",
            ),
            Rule(
                rule_id="RULE-002",
                rule_text="Route login, password and profile access issues to account.",
                success_condition="The true queue is account.",
                failure_condition="The true queue is not account.",
                evaluation_window=20,
                status="confirmed",
                min_success_rate=0.80,
                max_failure_rate=0.20,
                created_by="seed",
            ),
            Rule(
                rule_id="RULE-003",
                rule_text="Route error, crash, integration and API issues to technical.",
                success_condition="The true queue is technical.",
                failure_condition="The true queue is not technical.",
                evaluation_window=20,
                status="confirmed",
                min_success_rate=0.80,
                max_failure_rate=0.20,
                created_by="seed",
            ),
        ],
        trial_rules=[
            Rule(
                rule_id="RULE-004",
                rule_text="When a ticket contains both 'invoice' and 'API', prefer billing unless the text explicitly says integration failure.",
                success_condition="Routing matches expected_queue.",
                failure_condition="Routing differs from expected_queue.",
                evaluation_window=10,
                status="trial",
                min_success_rate=0.80,
                max_failure_rate=0.20,
                created_by="seed",
            )
        ],
    )


def seed_if_needed() -> None:
    init_db()
    try:
        get_champion()
    except RuntimeError:
        save_playbook(initial_playbook(), champion=True)


if __name__ == "__main__":
    seed_if_needed()
    print("Database ready.")
