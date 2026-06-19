from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ScoringResultItem(BaseModel):
    id: int
    risk_safety: int = Field(ge=0, le=10, default=0)
    risk_fraud: int = Field(ge=0, le=10, default=0)
    risk_attitude: int = Field(ge=0, le=10, default=0)
    risk_vehicle: int = Field(ge=0, le=10, default=0)
    risk_compliance: int = Field(ge=0, le=10, default=0)

class ScoringBatchOutput(BaseModel):
    results: List[ScoringResultItem]

class RouterOutput(BaseModel):
    team: str
    sla_hours: int = 24
    routed_by: str
    is_override: bool = False
    priority: Optional[str] = None
    description: Optional[str] = None

class ActionItem(BaseModel):
    action: str
    deadline: Optional[str] = None

class AnalystAnalysis(BaseModel):
    root_cause_summary: str
    risk_level: str
    action_items: List[ActionItem] = Field(default_factory=list)

class AnalystOutput(BaseModel):
    status: str
    reason: Optional[str] = None
    analysis: Optional[AnalystAnalysis] = None

class TopTopic(BaseModel):
    topic: str
    count: int

class RecentSample(BaseModel):
    id: Optional[str] = None
    text: str
    area: Optional[str] = None

class InsightOutput(BaseModel):
    team: str
    period_hours: int
    total_feedback: int
    severity_distribution: Dict[str, int]
    top_topics: List[TopTopic]
    recent_samples: List[RecentSample]

class AlertOutput(BaseModel):
    action: str # "skip" or "create"
    reason: Optional[str] = None
    area: Optional[str] = None
    severity: Optional[str] = None
    case_count: Optional[int] = None
    has_p5: Optional[bool] = None

class TicketOutput(BaseModel):
    ticket_id: Optional[str] = None
    action: str # "created" | "updated" | "skipped"
    assigned_team: Optional[str] = None
    status: Optional[str] = None
    error: Optional[str] = None
