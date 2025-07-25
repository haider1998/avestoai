# backend/models/schemas.py
from pydantic import BaseModel, Field, validator, EmailStr
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid


# Enums
class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    ANALYST = "analyst"


class OpportunityType(str, Enum):
    SAVINGS_OPTIMIZATION = "savings_optimization"
    INVESTMENT_GROWTH = "investment_growth"
    EXPENSE_REDUCTION = "expense_reduction"
    DEBT_REDUCTION = "debt_reduction"
    TAX_OPTIMIZATION = "tax_optimization"
    RISK_MITIGATION = "risk_mitigation"
    INCOME_ENHANCEMENT = "income_enhancement"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class RiskLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


# Base Models
class BaseResponse(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    success: bool = True
    data_sources: List[str] = Field(default_factory=list)


# Authentication Models
class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password")
    name: str = Field(..., min_length=1, max_length=100, description="Full name")
    age: Optional[int] = Field(None, ge=18, le=100, description="Age")
    phone: Optional[str] = Field(None, description="Phone number")
    city: Optional[str] = Field(None, description="City")
    annual_income: Optional[float] = Field(None, ge=0, description="Annual income in INR")
    risk_tolerance: str = Field(default="moderate", description="Risk tolerance")

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")


class UserProfile(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    email: EmailStr = Field(..., description="User email")
    name: str = Field(..., description="Full name")
    age: Optional[int] = Field(None, description="Age")
    phone: Optional[str] = Field(None, description="Phone number")
    city: Optional[str] = Field(None, description="City")
    annual_income: Optional[float] = Field(None, description="Annual income")
    risk_tolerance: str = Field(..., description="Risk tolerance level")
    role: UserRole = Field(default=UserRole.USER, description="User role")
    is_active: bool = Field(default=True, description="Account status")
    created_at: datetime = Field(..., description="Account creation date")
    last_login: Optional[datetime] = Field(None, description="Last login date")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    goals: Dict[str, Any] = Field(default_factory=dict, description="Financial goals")


class AuthResponse(BaseResponse):
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserProfile = Field(..., description="User profile")


# Opportunity Models
class Opportunity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique opportunity ID")
    type: OpportunityType = Field(..., description="Type of opportunity")
    priority: Priority = Field(..., description="Priority level")
    title: str = Field(..., description="Opportunity title")
    description: str = Field(..., description="Detailed description")
    potential_annual_value: float = Field(..., description="Annual value in INR")
    effort_level: str = Field(..., description="Implementation effort")
    time_to_implement: str = Field(..., description="Implementation timeline")
    confidence_score: float = Field(..., ge=0, le=1, description="AI confidence")
    risk_level: RiskLevel = Field(..., description="Risk assessment")
    category: str = Field(..., description="Opportunity category")
    action_steps: List[str] = Field(default_factory=list, description="Implementation steps")
    financial_impact: Dict[str, Any] = Field(default_factory=dict, description="Financial projections")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisites")
    timeline_milestones: List[Dict[str, Any]] = Field(default_factory=list, description="Milestones")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")


class OpportunityRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="User ID (auto-filled from auth)")
    analysis_type: str = Field(default="comprehensive", description="Analysis type")
    include_predictions: bool = Field(default=True, description="Include predictions")
    focus_areas: List[str] = Field(default_factory=list, description="Focus areas")
    time_horizon: str = Field(default="1_year", description="Time horizon")


class OpportunityResponse(BaseResponse):
    opportunities: List[Opportunity] = Field(..., description="List of opportunities")
    total_annual_value: float = Field(..., description="Total potential value")
    processing_time: float = Field(..., description="Processing time in ms")
    confidence_score: float = Field(..., description="Overall confidence")
    recommendations: List[str] = Field(default_factory=list, description="Key recommendations")
    market_context: Dict[str, Any] = Field(default_factory=dict, description="Market context")


# Decision Analysis Models
class DecisionRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="User ID (auto-filled)")
    amount: float = Field(..., gt=0, description="Amount in INR")
    category: str = Field(..., description="Purchase/investment category")
    description: str = Field(..., description="Detailed description")
    purchase_date: Optional[datetime] = Field(None, description="Planned purchase date")
    financing_method: str = Field(default="cash", description="How it will be financed")
    user_context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 100_000_000:  # 10 Crore limit
            raise ValueError('Amount too large for analysis')
        return v


class DecisionAlternative(BaseModel):
    option: str = Field(..., description="Alternative description")
    score: int = Field(..., ge=0, le=100, description="Score for alternative")
    reasoning: str = Field(..., description="Reasoning")
    pros: List[str] = Field(default_factory=list, description="Advantages")
    cons: List[str] = Field(default_factory=list, description="Disadvantages")
    financial_impact: Dict[str, Any] = Field(default_factory=dict, description="Financial impact")


class DecisionResponse(BaseResponse):
    score: int = Field(..., ge=0, le=100, description="Decision score")
    explanation: str = Field(..., description="Detailed explanation")
    reasoning: Dict[str, Any] = Field(default_factory=dict, description="Scoring breakdown")
    alternatives: List[DecisionAlternative] = Field(default_factory=list, description="Alternatives")
    long_term_impact: Dict[str, Any] = Field(default_factory=dict, description="Long-term projections")
    risk_factors: List[str] = Field(default_factory=list, description="Risk factors")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    optimal_timing: Dict[str, Any] = Field(default_factory=dict, description="Timing analysis")
    processing_time: float = Field(..., description="Processing time in ms")


# Chat Models
class ChatRequest(BaseModel):
    user_id: Optional[str] = Field(None, description="User ID (auto-filled)")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    include_charts: bool = Field(default=True, description="Include charts")
    context_type: str = Field(default="general", description="Context type")


class ChatResponse(BaseResponse):
    response: str = Field(..., description="AI response")
    suggestions: List[str] = Field(default_factory=list, description="Follow-up suggestions")
    charts: List[Dict[str, Any]] = Field(default_factory=list, description="Chart data")
    confidence: float = Field(..., ge=0, le=1, description="Response confidence")
    processing_time: float = Field(..., description="Processing time in ms")
    conversation_id: str = Field(..., description="Conversation ID")
    requires_action: bool = Field(default=False, description="Requires user action")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Suggested actions")


# Dashboard Models
class FinancialSummary(BaseModel):
    net_worth: float = Field(..., description="Current net worth")
    liquid_assets: float = Field(..., description="Liquid assets")
    investments: float = Field(..., description="Total investments")
    debt: float = Field(..., description="Total debt")
    monthly_income: float = Field(..., description="Monthly income")
    monthly_expenses: float = Field(..., description="Monthly expenses")
    cash_flow: float = Field(..., description="Net cash flow")
    emergency_fund_months: float = Field(..., description="Emergency fund coverage")


class DashboardResponse(BaseResponse):
    user_id: str = Field(..., description="User ID")
    financial_summary: FinancialSummary = Field(..., description="Financial summary")
    health_score: int = Field(..., ge=0, le=100, description="Financial health score")
    recent_opportunities: List[Opportunity] = Field(default_factory=list, description="Recent opportunities")
    insights: List[str] = Field(default_factory=list, description="Key insights")
    alerts: List[Dict[str, Any]] = Field(default_factory=list, description="Important alerts")
    charts_data: List[Dict[str, Any]] = Field(default_factory=list, description="Chart data")
    trends: Dict[str, Any] = Field(default_factory=dict, description="Trend analysis")
    goals_progress: Dict[str, Any] = Field(default_factory=dict, description="Goals progress")
    last_updated: datetime = Field(..., description="Last update time")


# Error Models
class ErrorDetail(BaseModel):
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    field: Optional[str] = Field(None, description="Field causing error")


class ErrorResponse(BaseModel):
    success: bool = Field(default=False, description="Success status")
    error: str = Field(..., description="Error message")
    details: List[ErrorDetail] = Field(default_factory=list, description="Error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
