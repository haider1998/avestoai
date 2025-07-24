# backend/models/schemas.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class ProcessingMode(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"


class OpportunityType(str, Enum):
    SAVINGS_OPTIMIZATION = "savings_optimization"
    INVESTMENT_GROWTH = "investment_growth"
    EXPENSE_REDUCTION = "expense_reduction"
    DEBT_REDUCTION = "debt_reduction"
    TAX_OPTIMIZATION = "tax_optimization"
    RISK_MITIGATION = "risk_mitigation"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# Request Models
class OpportunityRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    analysis_type: str = Field(default="comprehensive", description="Type of analysis to perform")
    include_predictions: bool = Field(default=True, description="Include predictive insights")


class DecisionRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    amount: float = Field(..., gt=0, description="Amount in INR")
    category: str = Field(..., description="Category of expense/investment")
    description: str = Field(..., description="Description of the decision")
    user_context: Dict[str, Any] = Field(default_factory=dict, description="User financial context")

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 10_000_000:  # 1 Crore limit
            raise ValueError('Amount too large for analysis')
        return v


class ChatRequest(BaseModel):
    user_id: str = Field(..., description="User identifier")
    message: str = Field(..., min_length=1, max_length=1000, description="User message")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="Previous conversation")
    include_charts: bool = Field(default=True, description="Include visual charts in response")


class CreateUserRequest(BaseModel):
    email: str = Field(..., description="User email")
    name: str = Field(..., description="User full name")
    age: Optional[int] = Field(None, ge=18, le=100, description="User age")
    income: Optional[float] = Field(None, ge=0, description="Annual income in INR")
    city: Optional[str] = Field(None, description="City of residence")
    risk_tolerance: str = Field(default="moderate", description="Risk tolerance level")


# Response Models
class Opportunity(BaseModel):
    id: str = Field(..., description="Unique opportunity identifier")
    type: OpportunityType = Field(..., description="Type of opportunity")
    priority: Priority = Field(..., description="Priority level")
    title: str = Field(..., description="Opportunity title")
    description: str = Field(..., description="Detailed description")
    potential_annual_value: float = Field(..., description="Annual value in INR")
    effort_level: str = Field(..., description="Implementation effort required")
    time_to_implement: str = Field(..., description="Time required to implement")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence in prediction")
    risk_level: str = Field(..., description="Risk level of opportunity")
    category: str = Field(..., description="Opportunity category")
    action_steps: List[str] = Field(default_factory=list, description="Implementation steps")
    financial_impact: Dict[str, Any] = Field(default_factory=dict, description="Financial impact details")


class OpportunityResponse(BaseModel):
    opportunities: List[Opportunity] = Field(..., description="List of opportunities")
    total_annual_value: float = Field(..., description="Total potential annual value")
    processing_time: float = Field(..., description="Processing time in seconds")
    confidence_score: float = Field(..., ge=0, le=1, description="Overall confidence")
    hybrid_processing: bool = Field(default=True, description="Used hybrid processing")
    recommendations: List[str] = Field(default_factory=list, description="Top recommendations")


class DecisionAlternative(BaseModel):
    option: str = Field(..., description="Alternative option")
    score: int = Field(..., ge=0, le=100, description="Score for alternative")
    reasoning: str = Field(..., description="Reasoning for score")


class DecisionResponse(BaseModel):
    score: int = Field(..., ge=0, le=100, description="Decision score out of 100")
    quick_score: Optional[int] = Field(None, description="Quick local score")
    explanation: str = Field(..., description="Detailed explanation")
    alternatives: List[DecisionAlternative] = Field(default_factory=list, description="Alternative options")
    long_term_impact: Dict[str, Any] = Field(default_factory=dict, description="Long-term financial impact")
    processing_mode: ProcessingMode = Field(..., description="Processing mode used")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in analysis")
    processing_time: float = Field(default=0.0, description="Processing time in milliseconds")


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI response message")
    processing_location: ProcessingMode = Field(..., description="Where query was processed")
    suggestions: List[str] = Field(default_factory=list, description="Follow-up suggestions")
    charts: List[Dict[str, Any]] = Field(default_factory=list, description="Chart data")
    confidence: float = Field(..., ge=0, le=1, description="Response confidence")
    response_time: float = Field(default=0.0, description="Response time in milliseconds")


class UserResponse(BaseModel):
    user_id: str = Field(..., description="Created user ID")
    token: str = Field(..., description="JWT access token")
    created_at: datetime = Field(..., description="Account creation timestamp")


# Health Check Models
class ServiceHealth(BaseModel):
    status: str = Field(..., description="Service status")
    response_time: Optional[float] = Field(None, description="Response time in ms")
    last_check: datetime = Field(..., description="Last health check time")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall system status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    services: Dict[str, ServiceHealth] = Field(..., description="Individual service health")
