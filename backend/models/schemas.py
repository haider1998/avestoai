# backend/models/schemas.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid


# Enums
class FiMCPScenario(str, Enum):
    NO_ASSETS = "no_assets"
    ALL_ASSETS_LARGE = "all_assets_large"
    ALL_ASSETS_SMALL = "all_assets_small"
    MULTIPLE_ACCOUNTS = "multiple_accounts"
    NO_CREDIT = "no_credit"
    NO_BANK = "no_bank"
    DEBT_HEAVY = "debt_heavy"
    SIP_INVESTOR = "sip_investor"
    FIXED_INCOME = "fixed_income"
    GOLD_INVESTOR = "gold_investor"
    EPF_DORMANT = "epf_dormant"
    SALARY_SINK = "salary_sink"
    BALANCED = "balanced"
    STARTER = "starter"
    DUAL_INCOME = "dual_income"
    HIGH_SPENDER = "high_spender"


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


# Fi MCP Authentication Models
class FiAuthInitiateRequest(BaseModel):
    mobile_number: str = Field(..., pattern=r"^\d{10}$", description="10-digit mobile number")
    scenario: FiMCPScenario = Field(default=FiMCPScenario.BALANCED, description="Fi MCP test scenario")


class FiAuthInitiateResponse(BaseResponse):
    session_id: str = Field(..., description="Fi MCP session ID")
    login_url: Optional[str] = Field(None, description="Login URL if authentication required")
    mobile_number: str = Field(..., description="Mobile number")
    scenario: FiMCPScenario = Field(..., description="Selected scenario")
    requires_authentication: bool = Field(..., description="Whether authentication is required")
    message: str = Field(..., description="Status message")


class FiAuthVerifyRequest(BaseModel):
    session_id: str = Field(..., description="Fi MCP session ID")
    mobile_number: str = Field(..., pattern=r"^\d{10}$", description="10-digit mobile number")
    otp: str = Field(..., description="OTP (any value works in dev)")


class FiAuthVerifyResponse(BaseResponse):
    success: bool = Field(..., description="Authentication success status")
    session_id: str = Field(..., description="Fi MCP session ID")
    mobile_number: str = Field(..., description="Mobile number")
    scenario: Optional[FiMCPScenario] = Field(None, description="User scenario")
    net_worth: Optional[float] = Field(None, description="User net worth")
    accounts_count: Optional[int] = Field(None, description="Number of accounts")
    message: str = Field(..., description="Status message")


class FiAuthStatusResponse(BaseResponse):
    mobile_number: str = Field(..., description="Mobile number")
    is_authenticated: bool = Field(..., description="Authentication status")
    session_id: Optional[str] = Field(None, description="Session ID if authenticated")
    scenario: Optional[FiMCPScenario] = Field(None, description="Current scenario")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")


# Core Request Models (updated to use mobile number)
class OpportunityRequest(BaseModel):
    mobile_number: str = Field(..., pattern=r"^\d{10}$", description="10-digit mobile number")
    analysis_type: str = Field(default="comprehensive", description="Type of analysis to perform")
    include_predictions: bool = Field(default=True, description="Include predictive insights")
    focus_areas: List[str] = Field(default_factory=list, description="Focus areas")
    time_horizon: str = Field(default="1_year", description="Time horizon")


class DecisionRequest(BaseModel):
    mobile_number: str = Field(..., pattern=r"^\d{10}$", description="10-digit mobile number")
    amount: float = Field(..., gt=0, description="Amount in INR")
    category: str = Field(..., description="Category of expense/investment")
    description: str = Field(..., description="Description of the decision")
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


class ChatRequest(BaseModel):
    mobile_number: str = Field(..., pattern=r"^\d{10}$", description="10-digit mobile number")
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    conversation_id: Optional[str] = Field(None, description="Conversation ID")
    include_charts: bool = Field(default=True, description="Include charts")
    context_type: str = Field(default="general", description="Context type")


class SwitchScenarioRequest(BaseModel):
    mobile_number: str = Field(..., pattern=r"^\d{10}$", description="10-digit mobile number")
    scenario: FiMCPScenario = Field(..., description="New scenario to switch to")


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


class OpportunityResponse(BaseResponse):
    opportunities: List[Opportunity] = Field(..., description="List of opportunities")
    total_annual_value: float = Field(..., description="Total potential value")
    processing_time: float = Field(..., description="Processing time in ms")
    confidence_score: float = Field(..., description="Overall confidence")
    recommendations: List[str] = Field(default_factory=list, description="Key recommendations")
    market_context: Dict[str, Any] = Field(default_factory=dict, description="Market context")
    mobile_number: str = Field(..., description="Mobile number")


# Decision Analysis Models
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
    mobile_number: str = Field(..., description="Mobile number")


# Chat Models
class ChatResponse(BaseResponse):
    response: str = Field(..., description="AI response")
    suggestions: List[str] = Field(default_factory=list, description="Follow-up suggestions")
    charts: List[Dict[str, Any]] = Field(default_factory=list, description="Chart data")
    confidence: float = Field(..., ge=0, le=1, description="Response confidence")
    processing_time: float = Field(..., description="Processing time in ms")
    conversation_id: str = Field(..., description="Conversation ID")
    requires_action: bool = Field(default=False, description="Requires user action")
    actions: List[Dict[str, Any]] = Field(default_factory=list, description="Suggested actions")
    mobile_number: str = Field(..., description="Mobile number")


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
    mobile_number: str = Field(..., description="Mobile number")
    financial_summary: FinancialSummary = Field(..., description="Financial summary")
    health_score: int = Field(..., ge=0, le=100, description="Financial health score")
    recent_opportunities: List[Opportunity] = Field(default_factory=list, description="Recent opportunities")
    insights: List[str] = Field(default_factory=list, description="Key insights")
    alerts: List[Dict[str, Any]] = Field(default_factory=list, description="Important alerts")
    charts_data: List[Dict[str, Any]] = Field(default_factory=list, description="Chart data")
    trends: Dict[str, Any] = Field(default_factory=dict, description="Trend analysis")
    goals_progress: Dict[str, Any] = Field(default_factory=dict, description="Goals progress")
    last_updated: datetime = Field(..., description="Last update time")
    scenario: FiMCPScenario = Field(..., description="Current Fi MCP scenario")


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
