# backend/services/vertex_ai_service.py
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
from google.cloud import aiplatform
import json
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential
import os
from google.oauth2 import service_account
from backend.models.configs import Settings

logger = structlog.get_logger()


class VertexAIService:
    """Service for Vertex AI operations using Gemini models"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.project_id = settings.GOOGLE_CLOUD_PROJECT
        self.location = settings.VERTEX_AI_LOCATION

        # Initialize Vertex AI with proper authentication
        try:
            # Check if service account file exists
            service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if service_account_path and os.path.exists(service_account_path):
                # Use service account file
                credentials = service_account.Credentials.from_service_account_file(
                    service_account_path
                )
                vertexai.init(
                    project=self.project_id,
                    location=self.location,
                    credentials=credentials
                )
                logger.info("✅ Using service account credentials for Vertex AI")
            else:
                # Use default application credentials (from gcloud auth application-default login)
                vertexai.init(project=self.project_id, location=self.location)
                logger.info("✅ Using default application credentials for Vertex AI")
        except Exception as e:
            logger.error("❌ Failed to initialize Vertex AI with credentials", error=str(e))
            # Fallback to default initialization
            vertexai.init(project=self.project_id, location=self.location)

        # Initialize models
        self.gemini_pro = GenerativeModel("gemini-1.5-pro")
        self.gemini_flash = GenerativeModel("gemini-1.5-flash")

        # Safety settings for financial advice
        self.safety_settings = {
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH:
                generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT:
                generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT:
                generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT:
                generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        # Generation configs
        self.pro_config = {
            "max_output_tokens": 4096,
            "temperature": 0.3,
            "top_p": 0.8,
            "top_k": 40,
        }

        self.flash_config = {
            "max_output_tokens": 2048,
            "temperature": 0.2,
            "top_p": 0.9,
            "top_k": 40,
        }

        logger.info("✅ Vertex AI service initialized",
                    project=self.project_id,
                    location=self.location)

    async def health_check(self) -> Dict[str, Any]:
        """Check Vertex AI service health"""
        try:
            start_time = time.time()

            test_prompt = "Respond with 'Service operational' if you can process this request."
            response = await asyncio.to_thread(
                self.gemini_flash.generate_content,
                test_prompt,
                generation_config={"max_output_tokens": 50, "temperature": 0}
            )

            response_time = (time.time() - start_time) * 1000

            if "operational" in response.text.lower():
                return {
                    "status": "healthy",
                    "response_time": response_time,
                    "last_check": datetime.now()
                }
            else:
                return {
                    "status": "degraded",
                    "response_time": response_time,
                    "last_check": datetime.now(),
                    "message": "Unexpected response"
                }

        except Exception as e:
            logger.error("❌ Vertex AI health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "last_check": datetime.now(),
                "error": str(e)
            }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def analyze_financial_decision(self, decision_request) -> Dict[str, Any]:
        """Analyze financial decision using Gemini Pro"""
        logger.info("🎯 Analyzing financial decision with Gemini Pro",
                    amount=decision_request.amount,
                    category=decision_request.category)

        # Create comprehensive analysis prompt
        prompt = self._create_decision_analysis_prompt(decision_request)

        try:
            start_time = time.time()

            response = await asyncio.to_thread(
                self.gemini_pro.generate_content,
                prompt,
                generation_config=self.pro_config,
                safety_settings=self.safety_settings
            )

            processing_time = (time.time() - start_time) * 1000

            # Parse and validate response
            parsed_response = self._parse_json_response(response.text)

            # Add metadata
            parsed_response.update({
                "processing_time_ms": processing_time,
                "model_used": "gemini-1.5-pro",
                "analysis_timestamp": datetime.now().isoformat()
            })

            logger.info("✅ Decision analysis completed",
                        score=parsed_response.get("score", "unknown"),
                        processing_time=f"{processing_time:.1f}ms")

            return parsed_response

        except Exception as e:
            logger.error("❌ Decision analysis failed", error=str(e))
            return self._generate_fallback_decision_analysis(decision_request)

    async def calculate_financial_health_score(self, financial_data: Dict[str, Any]) -> int:
        """Calculate comprehensive financial health score"""
        logger.info("🏥 Calculating financial health score")

        prompt = self._create_health_score_prompt(financial_data)

        try:
            response = await asyncio.to_thread(
                self.gemini_flash.generate_content,
                prompt,
                generation_config=self.flash_config,
                safety_settings=self.safety_settings
            )

            parsed_response = self._parse_json_response(response.text)
            health_score = parsed_response.get("health_score", 50)

            logger.info("✅ Health score calculated", score=health_score)
            return max(0, min(100, health_score))

        except Exception as e:
            logger.error("❌ Health score calculation failed", error=str(e))
            return self._calculate_basic_health_score(financial_data)

    async def generate_dashboard_insights(self, financial_data: Dict[str, Any]) -> List[str]:
        """Generate insights for dashboard"""
        logger.info("💡 Generating dashboard insights")

        prompt = self._create_insights_prompt(financial_data)

        try:
            response = await asyncio.to_thread(
                self.gemini_flash.generate_content,
                prompt,
                generation_config=self.flash_config,
                safety_settings=self.safety_settings
            )

            parsed_response = self._parse_json_response(response.text)
            insights = parsed_response.get("insights", [])

            logger.info("✅ Dashboard insights generated", count=len(insights))
            return insights

        except Exception as e:
            logger.error("❌ Insights generation failed", error=str(e))
            return self._generate_fallback_insights(financial_data)

    async def calculate_real_time_health(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate real-time health metrics"""
        try:
            prompt = f"""
            Analyze this real-time financial data and provide health metrics:

            Data: {json.dumps(current_data, indent=2)}

            Provide response in JSON:
            {{
                "score": 75,
                "metrics": {{
                    "liquidity": 80,
                    "debt_ratio": 60,
                    "spending_trend": 70,
                    "investment_performance": 85
                }},
                "alerts": [
                    {{
                        "type": "warning|info|critical",
                        "message": "Alert message",
                        "action": "Suggested action"
                    }}
                ],
                "trends": {{
                    "net_worth": "increasing|decreasing|stable",
                    "spending": "increasing|decreasing|stable",
                    "income": "increasing|decreasing|stable"
                }}
            }}
            """

            response = await asyncio.to_thread(
                self.gemini_flash.generate_content,
                prompt,
                generation_config=self.flash_config
            )

            return self._parse_json_response(response.text)

        except Exception as e:
            logger.error("❌ Real-time health calculation failed", error=str(e))
            return self._generate_basic_real_time_health(current_data)

    async def detect_financial_anomalies(self, current_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect financial anomalies and unusual patterns"""
        try:
            prompt = f"""
            Analyze this financial data for anomalies and unusual patterns:

            Data: {json.dumps(current_data, indent=2)}

            Look for:
            - Unusual spending patterns
            - Income irregularities  
            - Investment volatility
            - Account balance anomalies

            Return JSON array of anomalies:
            [
                {{
                    "type": "spending|income|investment|balance",
                    "severity": "low|medium|high|critical",
                    "description": "What was detected",
                    "value": 15000,
                    "threshold": 10000,
                    "recommendation": "What to do about it",
                    "confidence": 0.85
                }}
            ]
            """

            response = await asyncio.to_thread(
                self.gemini_flash.generate_content,
                prompt,
                generation_config=self.flash_config
            )

            parsed_response = self._parse_json_response(response.text)
            return parsed_response if isinstance(parsed_response, list) else []

        except Exception as e:
            logger.error("❌ Anomaly detection failed", error=str(e))
            return []

    async def generate_chat_response(self, message: str, financial_context: Dict[str, Any],
                                     conversation_history: List[Dict[str, str]] = None,
                                     user_preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate conversational response for chat"""
        logger.info("💬 Generating chat response", message_length=len(message))

        prompt = self._create_chat_prompt(message, financial_context, conversation_history, user_preferences)

        try:
            response = await asyncio.to_thread(
                self.gemini_flash.generate_content,
                prompt,
                generation_config=self.flash_config,
                safety_settings=self.safety_settings
            )

            parsed_response = self._parse_json_response(response.text)

            # Ensure required fields
            parsed_response.setdefault("response", "I'm here to help with your financial questions.")
            parsed_response.setdefault("suggestions", [])
            parsed_response.setdefault("charts", [])
            parsed_response.setdefault("confidence", 0.8)
            parsed_response.setdefault("requires_action", False)
            parsed_response.setdefault("actions", [])

            logger.info("✅ Chat response generated")
            return parsed_response

        except Exception as e:
            logger.error("❌ Chat response generation failed", error=str(e))
            return {
                "response": "I'm experiencing some technical difficulties. Please try rephrasing your question.",
                "suggestions": ["What's my current net worth?", "Show me my spending trends",
                                "How can I save more money?"],
                "charts": [],
                "confidence": 0.5,
                "requires_action": False,
                "actions": []
            }

    # Private helper methods for prompt creation
    def _create_decision_analysis_prompt(self, decision_request) -> str:
        """Create comprehensive decision analysis prompt"""
        return f"""
        You are AvestoAI, a revolutionary financial intelligence advisor. Analyze this financial decision comprehensively.

        DECISION DETAILS:
        - Description: {decision_request.description}
        - Amount: ₹{decision_request.amount:,}
        - Category: {decision_request.category}
        - Financing Method: {decision_request.financing_method}
        - User Context: {json.dumps(decision_request.user_context, indent=2)}

        Current Date: {datetime.now().strftime('%Y-%m-%d')}

        ANALYSIS FRAMEWORK:
        Provide detailed analysis in JSON format:
        {{
            "score": 75,
            "explanation": "Comprehensive reasoning including pros/cons analysis, affordability assessment, and goal alignment",
            "reasoning": {{
                "affordability": 80,
                "opportunity_cost": 60,
                "goal_alignment": 70,
                "timing": 65,
                "risk_assessment": 75
            }},
            "alternatives": [
                {{
                    "option": "Specific alternative description",
                    "score": 85,
                    "reasoning": "Why this alternative is better/worse",
                    "pros": ["Advantage 1", "Advantage 2"],
                    "cons": ["Disadvantage 1", "Disadvantage 2"],
                    "financial_impact": {{
                        "upfront_cost": 50000,
                        "monthly_impact": -2000,
                        "annual_savings": 24000
                    }}
                }}
            ],
            "long_term_impact": {{
                "net_worth_impact_1_year": -15000,
                "net_worth_impact_5_years": -75000,
                "opportunity_cost_5_years": 125000,
                "best_case_scenario": "Description of best outcome with quantified benefits",
                "worst_case_scenario": "Description of worst outcome with quantified risks",
                "break_even_timeline": "Timeline for investment to break even"
            }},
            "risk_factors": [
                "Specific risk 1 with quantified impact",
                "Specific risk 2 with mitigation strategy"
            ],
            "recommendations": [
                "Specific actionable recommendation 1",
                "Specific actionable recommendation 2"
            ],
            "optimal_timing": {{
                "current_timing_score": 70,
                "better_timing": "Wait 3 months for bonus",
                "timing_rationale": "Market conditions and personal finances suggest waiting"
            }},
            "confidence": 0.85
        }}

        SCORING CRITERIA (0-100):
        - 90-100: Excellent decision, strongly recommended
        - 70-89: Good decision with minor considerations
        - 50-69: Neutral decision, depends on priorities  
        - 30-49: Poor decision, significant concerns
        - 0-29: Very poor decision, strongly discouraged

        Consider: affordability, opportunity cost, goal alignment, market timing, risk factors, and personal circumstances.
        Provide specific numbers and calculations wherever possible.
        """

    def _create_health_score_prompt(self, financial_data: Dict[str, Any]) -> str:
        """Create financial health score calculation prompt"""
        return f"""
        Calculate comprehensive financial health score for this user:

        FINANCIAL DATA:
        {json.dumps(financial_data, indent=2)}

        HEALTH SCORE CALCULATION:
        Provide response in JSON:
        {{
            "health_score": 75,
            "breakdown": {{
                "liquidity": 80,
                "debt_management": 70,
                "investment_diversification": 75,
                "emergency_preparedness": 60,
                "goal_progress": 85,
                "spending_discipline": 70
            }},
            "strengths": [
                "Strong investment portfolio",
                "Good debt-to-income ratio"
            ],
            "improvement_areas": [
                "Build larger emergency fund", 
                "Optimize tax savings"
            ],
            "recommendations": [
                "Increase emergency fund by ₹2 lakhs",
                "Consider ELSS investments for tax savings"
            ]
        }}

        SCORING FACTORS:
        - Liquidity (cash + emergency fund): 20%
        - Debt management (ratios + payment history): 20%
        - Investment diversification & performance: 20%
        - Emergency preparedness (3-6 months expenses): 15%
        - Financial goal progress: 15%
        - Spending discipline & budgeting: 10%

        Score Range: 0-100 where 100 is optimal financial health.
        """

    def _create_insights_prompt(self, financial_data: Dict[str, Any]) -> str:
        """Create dashboard insights generation prompt"""
        return f"""
        Generate actionable financial insights for dashboard:

        FINANCIAL DATA:
        {json.dumps(financial_data, indent=2)}

        Generate insights in JSON:
        {{
            "insights": [
                "Your net worth increased by ₹45,000 this month - great progress!",
                "Consider moving ₹50,000 from savings to high-yield investments",
                "Your spending on dining increased 23% - budget ₹8,000/month to stay on track"
            ]
        }}

        INSIGHT TYPES TO INCLUDE:
        1. Performance highlights (positive achievements)
        2. Optimization opportunities (actionable improvements)
        3. Risk alerts (important warnings)
        4. Goal progress updates (milestone tracking)
        5. Market opportunities (timely suggestions)

        REQUIREMENTS:
        - Be specific with amounts and percentages
        - Include actionable next steps
        - Focus on most impactful insights
        - Use encouraging but realistic tone
        - Limit to 5-7 insights maximum
        """

    def _create_chat_prompt(self, message: str, financial_context: Dict[str, Any],
                            conversation_history: List[Dict[str, str]] = None,
                            user_preferences: Dict[str, Any] = None) -> str:
        """Create conversational chat prompt"""

        # Build conversation context
        context = ""
        if conversation_history:
            for turn in conversation_history[-5:]:  # Last 5 turns
                context += f"User: {turn.get('user', '')}\nAI: {turn.get('ai', '')}\n"

        return f"""
        You are AvestoAI, a revolutionary financial intelligence assistant. Respond naturally and helpfully.

        USER'S FINANCIAL CONTEXT:
        {json.dumps(financial_context, indent=2)}

        USER PREFERENCES:
        {json.dumps(user_preferences or {}, indent=2)}

        RECENT CONVERSATION:
        {context}

        CURRENT USER MESSAGE: {message}

        Provide response in JSON format:
        {{
            "response": "Natural, helpful response to the user's question",
            "suggestions": [
                "How can I improve my credit score?",
                "Show me my investment performance"
            ],
            "charts": [
                {{
                    "type": "line|bar|pie|doughnut",
                    "title": "Chart title",
                    "data": {{
                        "labels": ["Jan", "Feb", "Mar"],
                        "values": [100, 200, 150]
                    }},
                    "description": "What this chart shows",
                    "config": {{"currency": "INR", "timeframe": "6_months"}}
                }}
            ],
            "confidence": 0.85,
            "requires_action": false,
            "actions": [
                {{
                    "type": "navigate|create_goal|schedule_reminder",
                    "title": "Action title",
                    "description": "What this action does",
                    "data": {{"url": "/goals", "goal_type": "emergency_fund"}}
                }}
            ]
        }}

        RESPONSE GUIDELINES:
        - Be conversational and empathetic
        - Provide specific financial advice with numbers
        - Include relevant calculations when helpful
        - Suggest visualizations for complex data
        - Ask clarifying questions when needed
        - Stay focused on financial topics
        - Use encouraging but realistic tone
        - Provide actionable next steps
        """

    # Utility methods
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from AI response"""
        try:
            # Find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start >= 0 and end > start:
                json_str = response_text[start:end]
                parsed = json.loads(json_str)
                return parsed
            else:
                logger.warning("No JSON found in response", response_preview=response_text[:200])
                return {"error": "No JSON found", "raw_response": response_text[:500]}

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response", error=str(e), response_preview=response_text[:200])
            return {"error": "Invalid JSON", "parse_error": str(e)}

    def _calculate_basic_health_score(self, financial_data: Dict[str, Any]) -> int:
        """Calculate basic health score without AI"""
        try:
            # Simple rule-based calculation
            score = 50  # Base score

            # Check emergency fund
            summary = financial_data.get("summary", {})
            emergency_months = summary.get("emergency_fund_months", 0)

            if emergency_months >= 6:
                score += 20
            elif emergency_months >= 3:
                score += 10

            # Check debt ratio
            net_worth = summary.get("net_worth", 0)
            debt = summary.get("debt", 0)

            if debt == 0:
                score += 15
            elif net_worth > 0 and (debt / net_worth) < 0.3:
                score += 10

            # Check investment allocation
            investments = summary.get("investments", 0)
            liquid_assets = summary.get("liquid_assets", 0)

            if investments > liquid_assets:
                score += 15

            return max(0, min(100, score))

        except Exception as e:
            logger.error("❌ Basic health score calculation failed", error=str(e))
            return 50

    def _generate_fallback_decision_analysis(self, decision_request) -> Dict[str, Any]:
        """Generate fallback decision analysis"""
        amount = decision_request.amount
        category = decision_request.category.lower()

        # Simple rule-based scoring
        base_score = 50

        if category in ["investment", "education", "health", "insurance"]:
            base_score += 20
        elif category in ["entertainment", "luxury", "gaming"]:
            base_score -= 20

        if amount > 100000:
            base_score -= 15
        elif amount < 10000:
            base_score += 10

        final_score = max(0, min(100, base_score))

        return {
            "score": final_score,
            "explanation": f"Based on {category} category and amount of ₹{amount:,}, this decision scores {final_score}/100.",
            "reasoning": {
                "affordability": 70,
                "opportunity_cost": 60,
                "goal_alignment": final_score,
                "timing": 65,
                "risk_assessment": 70
            },
            "alternatives": [{
                "option": "Save for 3 months and pay cash",
                "score": min(100, final_score + 15),
                "reasoning": "Reduces financial stress and interest costs"
            }],
            "long_term_impact": {
                "net_worth_impact_5_years": -amount * 0.5,
                "opportunity_cost_5_years": amount * 1.5
            },
            "confidence": 0.6
        }

    def _generate_fallback_insights(self, financial_data: Dict[str, Any]) -> List[str]:
        """Generate fallback insights"""
        return [
            "Your financial health is stable. Consider reviewing your investment allocation.",
            "Emergency fund could be strengthened - aim for 6 months of expenses.",
            "Regular investment reviews can help optimize your portfolio performance."
        ]

    def _generate_basic_real_time_health(self, current_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic real-time health metrics"""
        return {
            "score": 75,
            "metrics": {
                "liquidity": 80,
                "debt_ratio": 70,
                "spending_trend": 65,
                "investment_performance": 75
            },
            "alerts": [],
            "trends": {
                "net_worth": "stable",
                "spending": "stable",
                "income": "stable"
            }
        }

    async def cleanup(self):
        """Cleanup resources"""
        logger.info("🧹 Vertex AI service cleaned up")
