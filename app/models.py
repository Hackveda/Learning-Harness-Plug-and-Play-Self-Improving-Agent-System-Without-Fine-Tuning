from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


RuleStatus = Literal["trial", "confirmed", "falsified", "inconclusive", "retired"]


class FixedReference(BaseModel):
    key: str
    value: Any
    description: str = ""


class Rule(BaseModel):
    rule_id: str
    rule_text: str
    success_condition: str
    failure_condition: str
    evaluation_window: int = Field(default=20, ge=1)
    status: RuleStatus = "trial"
    episodes_evaluated: int = 0
    successes: int = 0
    failures: int = 0
    min_success_rate: float = Field(default=0.80, ge=0.0, le=1.0)
    max_failure_rate: float = Field(default=0.30, ge=0.0, le=1.0)
    high_risk: bool = False
    supporting_evidence: list[str] = Field(default_factory=list)
    created_by: str = "system"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.max_failure_rate > 1 - self.min_success_rate + 1e-9:
            raise ValueError(
                "max_failure_rate should not exceed 1 - min_success_rate; "
                "otherwise promotion and failure bands overlap."
            )
        return self


class Playbook(BaseModel):
    version: str
    fixed_reference_data: list[FixedReference] = Field(default_factory=list)
    proven_rules: list[Rule] = Field(default_factory=list)
    trial_rules: list[Rule] = Field(default_factory=list)
    retired_rules: list[Rule] = Field(default_factory=list)
    champion_score: float = 0.0
    previous_champion_version: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Decision(BaseModel):
    step: int
    rule_id: str | None = None
    action: str
    explanation: str


class EpisodeCreate(BaseModel):
    agent_id: str = "support-routing-agent"
    input_context: dict[str, Any]
    strategy_version: str | None = None


class EpisodeLog(BaseModel):
    episode_id: str
    agent_id: str
    input_context: dict[str, Any]
    strategy_version: str
    rules_used: list[str]
    decisions: list[Decision]
    final_outcome: str
    reward_score: float
    latency_ms: int
    cost: float
    stopped_early: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RuleCreate(BaseModel):
    rule_text: str
    success_condition: str
    failure_condition: str
    evaluation_window: int = Field(default=20, ge=1)
    min_success_rate: float = Field(default=0.80, ge=0.0, le=1.0)
    max_failure_rate: float = Field(default=0.30, ge=0.0, le=1.0)
    high_risk: bool = False
    created_by: str = "user"


class ReviewDecision(BaseModel):
    rule_id: str
    label: Literal["confirmed", "falsified", "inconclusive"]
    episodes_evaluated: int
    successes: int
    failures: int
    success_rate: float
    reason: str


class ReviewSummary(BaseModel):
    playbook_before: str
    playbook_after: str
    decisions: list[ReviewDecision]
    candidate_score: float
    champion_score: float
    promoted_to_champion: bool
    rolled_back: bool
