from __future__ import annotations

import hashlib
import json
import time
import uuid

from app.models import Decision, EpisodeCreate, EpisodeLog, Playbook


KEYWORDS = {
    "billing": ["refund", "invoice", "payment", "charged", "billing", "price"],
    "account": ["login", "password", "profile", "account", "sign in", "locked"],
    "technical": ["error", "crash", "api", "integration", "bug", "timeout"],
}


def _redact(context: dict) -> dict:
    cleaned = dict(context)
    for key in list(cleaned):
        lowered = key.lower()
        if any(term in lowered for term in ("password", "card_number", "secret", "token")):
            cleaned[key] = "[REDACTED]"
    return cleaned


def route_ticket(context: dict, playbook: Playbook) -> tuple[str, list[str], list[Decision]]:
    text = f"{context.get('subject', '')} {context.get('description', '')}".lower()
    scores = {queue: sum(term in text for term in terms) for queue, terms in KEYWORDS.items()}

    rules_used: list[str] = []
    decisions: list[Decision] = []

    # Trial rule demonstrates how a candidate rule can change behaviour.
    if "invoice" in text and "api" in text:
        if "integration failure" in text or "api error" in text:
            queue = "technical"
        else:
            queue = "billing"
        if any(r.rule_id == "RULE-004" for r in playbook.trial_rules):
            rules_used.append("RULE-004")
            decisions.append(
                Decision(
                    step=1,
                    rule_id="RULE-004",
                    action=f"route:{queue}",
                    explanation="Applied the invoice/API disambiguation trial rule.",
                )
            )
            return queue, rules_used, decisions

    queue = max(scores, key=scores.get) if max(scores.values()) > 0 else "general"
    mapping = {"billing": "RULE-001", "account": "RULE-002", "technical": "RULE-003"}
    rule_id = mapping.get(queue)
    if rule_id:
        rules_used.append(rule_id)

    decisions.append(
        Decision(
            step=1,
            rule_id=rule_id,
            action=f"route:{queue}",
            explanation=f"Keyword evidence scores were {scores}.",
        )
    )
    return queue, rules_used, decisions


def run_episode(payload: EpisodeCreate, playbook: Playbook) -> EpisodeLog:
    start = time.perf_counter()
    context = _redact(payload.input_context)
    queue, rules_used, decisions = route_ticket(context, playbook)

    expected = context.get("expected_queue")
    success = expected is None or queue == expected
    reward = 1.0 if success else 0.0
    outcome = "resolved_correctly" if success else "misrouted"

    # Optional watcher: stop an obviously invalid trajectory.
    allowed = next(
        (x.value for x in playbook.fixed_reference_data if x.key == "allowed_queues"),
        ["billing", "technical", "account", "general"],
    )
    stopped_early = queue not in allowed
    if stopped_early:
        outcome = "stopped_by_watcher"
        reward = 0.0

    latency_ms = max(1, int((time.perf_counter() - start) * 1000))
    cost = round(0.0002 + 0.00001 * len(json.dumps(context)), 6)

    return EpisodeLog(
        episode_id=str(uuid.uuid4()),
        agent_id=payload.agent_id,
        input_context=context,
        strategy_version=playbook.version,
        rules_used=rules_used,
        decisions=decisions,
        final_outcome=outcome,
        reward_score=reward,
        latency_ms=latency_ms,
        cost=cost,
        stopped_early=stopped_early,
    )
