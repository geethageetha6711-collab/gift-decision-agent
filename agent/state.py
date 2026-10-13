"""
State definitions and Pydantic schemas for the Gift Decision Agent.
"""

from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


class GiftCandidate(BaseModel):
    """Represents an individual gift candidate with multi-attribute evaluations."""
    gift_name: str
    gift_category: str
    estimated_cost_min: float
    estimated_cost_max: float
    description: str
    why_it_matches: str
    satisfied_interests: List[str] = Field(default_factory=list)
    satisfied_preferences: List[str] = Field(default_factory=list)
    personalization_possibilities: str = ""
    practical_usefulness: int = Field(default=7, ge=1, le=10)
    sentimental_value: int = Field(default=7, ge=1, le=10)
    potential_drawbacks: str = ""
    budget_fit_status: str = "Within budget"  # "Under budget", "Within budget", "Slight stretch"
    price_confidence_indicator: str = "High (standard market estimate)"
    verification_status: str = "Unverified market estimate - check local retail/e-commerce before purchase"
    total_score: float = 0.0
    score_breakdown: Dict[str, float] = Field(default_factory=dict)
    positive_factors: List[str] = Field(default_factory=list)
    trade_offs: List[str] = Field(default_factory=list)

    @property
    def cost_display(self) -> str:
        if self.estimated_cost_min == self.estimated_cost_max:
            return f"₹{int(self.estimated_cost_min):,}"
        return f"₹{int(self.estimated_cost_min):,} – ₹{int(self.estimated_cost_max):,}"


class GiftPreferencesInput(BaseModel):
    """Input payload from user preference discovery form."""
    session_id: Optional[str] = None
    occasion: str = Field(..., description="Occasion such as Birthday, Anniversary, etc.")
    recipient: str = Field(..., description="Recipient like Friend, Best friend, Partner, etc.")
    relationship: str = Field(default="Close", description="Relationship closeness level")
    budget_min: float = Field(default=500.0, ge=0, description="Minimum budget in INR")
    budget_max: float = Field(..., gt=0, description="Maximum budget in INR")
    interests: List[str] = Field(..., min_length=1, description="List of recipient interests")
    preferences: List[str] = Field(default_factory=list, description="Gift purposes like Useful, Memorable, etc.")
    disliked_items: List[str] = Field(default_factory=list, description="Items or categories to avoid")
    already_owned: List[str] = Field(default_factory=list, description="Items recipient already owns")
    gift_type: str = Field(default="No preference", description="Physical, Personalized, Experience, etc.")
    preferred_style: Optional[str] = Field(default="", description="Preferred color or style")
    age_range: Optional[str] = Field(default="", description="Optional age range")
    deadline: Optional[str] = Field(default="", description="Purchase timeline")
    optional_notes: Optional[str] = Field(default="", description="Extra personal context")

    @field_validator("budget_max")
    @classmethod
    def validate_budget_range(cls, v, values):
        budget_min = values.data.get("budget_min", 0.0)
        if v < budget_min:
            raise ValueError("Maximum budget must be greater than or equal to minimum budget.")
        return v


class FeedbackInput(BaseModel):
    """Input payload when user rejects or provides feedback on a recommendation."""
    reason: str = Field(..., description="Feedback reason, e.g. 'Too expensive', 'Not my style', etc.")
    custom_feedback: Optional[str] = Field(default="", description="Optional free-form user message")
    rejected_gift_name: Optional[str] = Field(default="", description="Name of the rejected candidate")


class GiftAgentState(TypedDict):
    """
    Typed shared state for the LangGraph workflow.
    Ensures state transitions are strictly tracked across all workflow nodes.
    """
    session_id: str
    occasion: str
    recipient: str
    relationship: str
    budget_min: float
    budget_max: float
    interests: List[str]
    preferences: List[str]
    disliked_items: List[str]
    already_owned: List[str]
    gift_type: str
    preferred_style: str
    age_range: str
    deadline: str
    optional_notes: str

    # Constraint separation
    hard_constraints: Dict[str, Any]
    soft_preferences: Dict[str, Any]

    # Candidate tracking
    candidate_gifts: List[Dict[str, Any]]
    filtered_candidates: List[Dict[str, Any]]
    rejected_candidates: List[Dict[str, Any]]

    # Scoring and Ranking
    scoring_breakdown: Dict[str, Any]
    ranked_gifts: List[Dict[str, Any]]
    selected_gift: Optional[Dict[str, Any]]
    alternatives: List[Dict[str, Any]]

    # Feedback and History
    rejected_gifts: List[Dict[str, Any]]
    feedback_history: List[Dict[str, Any]]
    updated_preferences: Dict[str, Any]

    # Execution control & Reviewer
    generation_attempts: int
    decision_explanation: str
    review_notes: List[str]
    warning_messages: List[str]
    needs_regeneration: bool
    mode: str  # "gemini" or "deterministic_fallback"
    status: str

    # Final reporting
    final_report: Dict[str, Any]
