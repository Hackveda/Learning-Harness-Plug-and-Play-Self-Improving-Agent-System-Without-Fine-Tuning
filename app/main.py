from __future__ import annotations

import random
import uuid

from fastapi import FastAPI, HTTPException

from app.models import EpisodeCreate, Rule, RuleCreate
from app.player import run_episode
from app.reviewer import review_and_promote
from app.seed import seed_if_needed
from app.storage import (
    add_audit,
    get_champion,
    list_audits,
    list_episodes,
    list_playbooks,
    save_episode,
    save_playbook,
)

app = FastAPI(
    title="Learning Harness API",
    version="1.0.0",
    description="Plug-and-play self-improving agent harness without fine-tuning.",
)


@app.on_event("startup")
def startup() -> None:
    seed_if_needed()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/playbook/champion")
def champion():
    return get_champion()


@app.get("/playbooks")
def playbooks():
    return list_playbooks()


@app.post("/rules/trial")
def create_trial_rule(payload: RuleCreate):
    playbook = get_champion()
    next_number = 1 + max(
        [int(r.rule_id.split("-")[-1]) for r in playbook.proven_rules + playbook.trial_rules + playbook.retired_rules]
        or [0]
    )
    rule = Rule(rule_id=f"RULE-{next_number:03d}", **payload.model_dump())
    playbook.trial_rules.append(rule)
    save_playbook(playbook, champion=True)
    add_audit("trial_rule_created", rule.model_dump())
    return rule


@app.post("/episodes")
def create_episode(payload: EpisodeCreate):
    playbook = get_champion()
    if payload.strategy_version and payload.strategy_version != playbook.version:
        raise HTTPException(
            status_code=409,
            detail=f"Requested {payload.strategy_version}, champion is {playbook.version}.",
        )
    episode = run_episode(payload, playbook)
    save_episode(episode)
    return episode


@app.get("/episodes")
def episodes(limit: int = 100):
    return list_episodes(limit=limit)


@app.post("/simulate")
def simulate(count: int = 50, success_bias: float = 0.8):
    if count < 1 or count > 5000:
        raise HTTPException(status_code=400, detail="count must be between 1 and 5000")
    success_bias = min(1.0, max(0.0, success_bias))

    samples = [
        ("Invoice API access request", "Need an invoice for API usage", "billing"),
        ("API integration failure", "Invoice API error during integration failure", "technical"),
        ("Cannot sign in", "My password reset is not working", "account"),
        ("Payment failed", "Card was charged twice, need refund", "billing"),
        ("Application crash", "The app crashes with timeout error", "technical"),
        ("General question", "Please share your office hours", "general"),
    ]

    created = []
    for _ in range(count):
        subject, description, expected = random.choice(samples)
        # Introduce controlled label noise for testing rollback and thresholds.
        if random.random() > success_bias:
            expected = random.choice(["billing", "technical", "account", "general"])
        payload = EpisodeCreate(
            input_context={
                "subject": subject,
                "description": description,
                "expected_queue": expected,
            }
        )
        episode = run_episode(payload, get_champion())
        save_episode(episode)
        created.append(episode)
    return {"created": len(created), "average_reward": sum(x.reward_score for x in created) / len(created)}


@app.post("/review")
def review(min_relative_improvement: float = 0.02, min_sample_size: int = 10):
    return review_and_promote(
        get_champion(),
        min_relative_improvement=min_relative_improvement,
        min_sample_size=min_sample_size,
    )


@app.get("/audits")
def audits(limit: int = 200):
    return list_audits(limit=limit)
