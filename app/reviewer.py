from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from app.models import Playbook, ReviewDecision, ReviewSummary
from app.storage import add_audit, list_episodes, save_playbook


def bump_version(version: str) -> str:
    parts = [int(x) for x in version.split(".")]
    while len(parts) < 3:
        parts.append(0)
    parts[2] += 1
    return ".".join(map(str, parts[:3]))


def evaluate(playbook: Playbook) -> tuple[Playbook, list[ReviewDecision], float]:
    candidate = deepcopy(playbook)
    decisions: list[ReviewDecision] = []

    all_episodes = list_episodes(strategy_version=playbook.version, limit=5000)
    candidate_score = (
        sum(e.reward_score for e in all_episodes) / len(all_episodes)
        if all_episodes
        else playbook.champion_score
    )

    remaining_trials = []
    for rule in candidate.trial_rules:
        related = [e for e in all_episodes if rule.rule_id in e.rules_used]
        n = len(related)
        successes = sum(1 for e in related if e.reward_score >= 1.0)
        failures = n - successes
        rate = successes / n if n else 0.0

        if n < rule.evaluation_window:
            label = "inconclusive"
            reason = f"Needs {rule.evaluation_window} episodes; only {n} available."
            rule.status = "inconclusive"
            remaining_trials.append(rule)
        elif rate >= rule.min_success_rate:
            label = "confirmed"
            reason = f"Success rate {rate:.1%} met threshold {rule.min_success_rate:.1%}."
            rule.status = "confirmed"
            candidate.proven_rules.append(rule)
        elif failures / n >= rule.max_failure_rate:
            label = "falsified"
            reason = f"Failure rate {failures/n:.1%} met threshold {rule.max_failure_rate:.1%}."
            rule.status = "falsified"
            candidate.retired_rules.append(rule)
        else:
            label = "inconclusive"
            reason = "Result fell between promotion and failure thresholds."
            rule.status = "inconclusive"
            remaining_trials.append(rule)

        rule.episodes_evaluated = n
        rule.successes = successes
        rule.failures = failures
        rule.supporting_evidence = [e.episode_id for e in related[-10:]]

        decisions.append(
            ReviewDecision(
                rule_id=rule.rule_id,
                label=label,
                episodes_evaluated=n,
                successes=successes,
                failures=failures,
                success_rate=rate,
                reason=reason,
            )
        )

    candidate.trial_rules = remaining_trials
    candidate.previous_champion_version = playbook.version
    candidate.version = bump_version(playbook.version)
    candidate.created_at = datetime.now(timezone.utc).isoformat()
    return candidate, decisions, candidate_score


def review_and_promote(
    champion: Playbook,
    min_relative_improvement: float = 0.02,
    min_sample_size: int = 10,
) -> ReviewSummary:
    candidate, decisions, candidate_score = evaluate(champion)
    episodes = list_episodes(strategy_version=champion.version, limit=5000)

    required_score = champion.champion_score * (1 + min_relative_improvement)
    enough_samples = len(episodes) >= min_sample_size
    promoted = enough_samples and candidate_score >= required_score
    rolled_back = not promoted

    if promoted:
        candidate.champion_score = candidate_score
        save_playbook(candidate, champion=True)
        after_version = candidate.version
        add_audit(
            "champion_promoted",
            {
                "from": champion.version,
                "to": candidate.version,
                "score": candidate_score,
                "decisions": [d.model_dump() for d in decisions],
            },
        )
    else:
        # Save challenger for audit, but leave champion pointer unchanged.
        save_playbook(candidate, champion=False)
        after_version = champion.version
        add_audit(
            "challenger_rejected",
            {
                "champion": champion.version,
                "challenger": candidate.version,
                "candidate_score": candidate_score,
                "required_score": required_score,
                "sample_size": len(episodes),
                "decisions": [d.model_dump() for d in decisions],
            },
        )

    return ReviewSummary(
        playbook_before=champion.version,
        playbook_after=after_version,
        decisions=decisions,
        candidate_score=candidate_score,
        champion_score=champion.champion_score,
        promoted_to_champion=promoted,
        rolled_back=rolled_back,
    )
