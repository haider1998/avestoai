# backend/services/vertex_ai_client.py
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

logger = structlog.get_logger()


class VertexAIClient:
    def __init__(self, settings):
        self.settings = settings
        self.project_id = settings.GOOGLE_CLOUD_PROJECT
        self.location = settings.VERTEX_AI_LOCATION

        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)

        # Initialize models
        self.gemini_pro = GenerativeModel("gemini-1.5-pro")
        self.gemini_flash = GenerativeModel("gemini-1.5-flash")

        # Safety settings for financial advice
        self.safety_settings = {
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        # Generation config for consistent outputs
        self.generation_config = {
            "max_output_tokens": 2048,
            "temperature": 0.3,
            "top_p": 0.8,
            "top_k": 40,
        }

        logger.info("✅ Vertex AI client initialized",
                    project=self.project_id,
                    location=self.location)

    async def health_check(self) -> Dict[str, Any]:
        """Check Vertex AI service health"""
        try:
            start_time = time.time()

            # Simple test generation
            test_prompt = "Test prompt: Respond with 'Service healthy'"
            response = await asyncio.to_thread(
                self.gemini_flash.generate_content,
                test_prompt,
                generation_config={"max_output_tokens": 20, "temperature": 0}
            )

            response_time = (time.time() - start_time) * 1000  # Convert to ms

            if "healthy" in response.text.lower():
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
                    "message": "Unexpected response from model"
                }

        except Exception as e:
            logger.error("❌ Vertex AI health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "last_check": datetime.now(),
                "error": str(e)
            }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def analyze_market_opportunities(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market opportunities using Gemini Pro"""

        logger.info("🧠 Analyzing market opportunities with Gemini Pro")

        prompt = f"""
        As a world-class financial AI advisor, analyze market opportunities for this user profile.

        User Profile (anonymized): {json.dumps(user_profile, indent=2)}
        Current Market Date: {datetime.now().strftime('%Y-%m-%d')}
        Market Context: Indian financial markets, considering current economic conditions

        Provide comprehensive analysis in JSON format:
        {{
            "market_opportunities": [
                {{
                    "type": "investment|savings|insurance|debt_optimization",
                    "title": "Specific opportunity title",
                    "description": "Detailed description with quantified benefits",
                    "potential_annual_value": "Annual value in INR (number only)",
                    "risk_level": "low|medium|high",
                    "time_horizon": "Timeline to realize benefits",
                    "action_steps": ["specific step 1", "specific step 2"],
                    "confidence": 0.85,
                    "market_timing": "Current market timing analysis"
                }}
            ],
            "market_context": {{
                "current_trends": ["Major trend 1", "Major trend 2"],
                "risk_factors": ["Risk factor 1", "Risk factor 2"],
                "timing_analysis": "Detailed market timing insights",
                "sector_opportunities": ["Sector 1", "Sector 2"]
            }},
            "personalized_insights": {{
                "strengths": ["Financial strength 1", "Financial strength 2"],
                "improvement_areas": ["Area 1", "Area 2"],
                "next_best_actions": ["Priority action 1", "Priority action 2"],
                "risk_mitigation": ["Risk mitigation strategy 1", "Risk mitigation strategy 2"]
            }},
            "ai_confidence": 0.88
        }}

        Requirements:
        - Focus on actionable, quantified opportunities with clear ROI
        - Consider current Indian market conditions (interest rates, inflation, policy changes)
        - Provide specific amounts in INR
        - Include risk assessment for each opportunity
        - Ensure recommendations are suitable for the user's profile
        """

        try:
            start_time = time.time()

            response = await asyncio.to_thread(
                self.gemini_pro.generate_content,
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )

            processing_time = (time.time() - start_time) * 1000

            # Parse JSON response
            parsed_response = self._parse_json_response(response.text)
            parsed_response["processing_time_ms"] = processing_time

            logger.info("✅ Market opportunities analysis completed",
                        processing_time=f"{processing_time:.1f}ms",
                        opportunities_found=len(parsed_response.get("market_opportunities", [])))

            return parsed_response

        except Exception as e:
            logger.error("❌ Market opportunities analysis failed", error=str(e))
            return self._generate_fallback_opportunities(user_profile)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
    async def deep_decision_analysis(self, decision_request) -> Dict[str, Any]:
        """Deep analysis of financial decisions using Gemini Flash for speed"""

        logger.info("🎯 Analyzing financial decision with Gemini Flash",
                    amount=decision_request.amount,
                    category=decision_request.category)

        prompt = f"""
        Analyze this financial decision comprehensively and provide scoring with reasoning.

        Decision Details:
        - Description: {decision_request.description}
        - Amount: ₹{decision_request.amount:,}
        - Category: {decision_request.category}
        - User Context: {json.dumps(decision_request.user_context, indent=2)}

        Current Date: {datetime.now().strftime('%Y-%m-%d')}

        Provide detailed analysis in JSON format:
        {{
            "score": 75,
            "explanation": "Comprehensive reasoning for the score including pros/cons analysis",
            "alternatives": [
                {{
                    "option": "Specific alternative description",
                    "score": 85,
                    "reasoning": "Why this alternative is better/worse"
                }}
            ],
            "projections": {{
                "net_worth_impact_1_year": -15000,
                "net_worth_impact_5_years": -75000,
                "opportunity_cost_5_years": 125000,
                "best_case_scenario": "Description of best outcome",
                "worst_case_scenario": "Description of worst outcome",
                "break_even_timeline": "When investment breaks even"
            }},
            "risk_factors": ["Specific risk 1", "Specific risk 2"],
            "timing_analysis": "Is now the right time for this decision?",
            "action_recommendation": "Specific next step recommendation",
            "confidence": 0.82,
            "category_insights": "Insights specific to this category",
            "optimization_tips": ["Tip 1", "Tip 2"]
        }}

        Scoring Criteria (0-100):
        - 90-100: Excellent decision, strongly recommended
        - 70-89: Good decision with minor concerns
        - 50-69: Neutral decision, depends on priorities
        - 30-49: Poor decision, significant concerns
        - 0-29: Very poor decision, strongly discouraged

        Consider affordability, opportunity cost, goal alignment, timing, and risk factors.
        """

        try:
            start_time = time.time()

            response = await asyncio.to_thread(
                self.gemini_flash.generate_content,
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )

            processing_time = (time.time() - start_time) * 1000

            parsed_response = self._parse_json_response(response.text)
            parsed_response["processing_time_ms"] = processing_time

            logger.info("✅ Decision analysis completed",
                        score=parsed_response.get("score", "unknown"),
                        processing_time=f"{processing_time:.1f}ms")

            return parsed_response

        except Exception as e:
            logger.error("❌ Decision analysis failed", error=str(e))
            return self._generate_fallback_decision_analysis(decision_request)

    async def generate_chat_response(self, message: str, user_data: Dict[str, Any],
                                     conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Generate conversational response for chat interface"""

        logger.info("💬 Generating chat response", message_length=len(message))

        # Build conversation context
        context = ""
        if conversation_history:
            for turn in conversation_history[-5:]:  # Last 5 turns
                context += f"User: {turn.get('user', '')}\nAI: {turn.get('ai', '')}\n"

        # Create financial context summary
        financial_summary = self._create_financial_summary(user_data)

        prompt = f"""
        You are AvestoAI, a revolutionary financial intelligence assistant. Respond naturally and helpfully.

        User's Financial Context:
        {financial_summary}

        Recent Conversation:
        {context}

        Current User Message: {message}

        Provide response in JSON format:
        {{
            "response": "Natural, helpful response to the user's question",
            "suggestions": ["Follow-up question 1", "Follow-up question 2"],
            "charts": [
                {{
                    "type": "line|bar|pie",
                    "title": "Chart title",
                    "data": {{"labels": [], "values": []}},
                    "description": "What this chart shows"
                }}
            ],
            "confidence": 0.85,
            "requires_followup": false
        }}

        Guidelines:
        - Be conversational and empathetic
        - Provide actionable financial advice
        - Include specific numbers and calculations when relevant
        - Suggest visualizations when helpful
        - Ask clarifying questions if needed
        - Stay focused on financial topics
        """

        try:
            start_time = time.time()

            response = await asyncio.to_thread(
                self.gemini_flash.generate_content,
                prompt,
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )

            processing_time = (time.time() - start_time) * 1000

            parsed_response = self._parse_json_response(response.text)
            parsed_response["processing_time_ms"] = processing_time

            logger.info("✅ Chat response generated", processing_time=f"{processing_time:.1f}ms")

            return parsed_response

        except Exception as e:
            logger.error("❌ Chat response generation failed", error=str(e))
            return {
                "response": "I'm here to help with your financial questions. Could you please rephrase your question?",
                "suggestions": ["What's my net worth?", "Should I invest more?", "How can I save money?"],
                "charts": [],
                "confidence": 0.5
            }

    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from Gemini response"""
        try:
            # Find JSON in response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1

            if start >= 0 and end > start:
                json_str = response_text[start:end]
                return json.loads(json_str)
            else:
                logger.warning("No JSON found in response", response_preview=response_text[:200])
                return {"error": "No JSON found in response", "raw_response": response_text}

        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON response", error=str(e), response_preview=response_text[:200])
            return {"error": "Invalid JSON response", "parse_error": str(e)}

    def _generate_fallback_opportunities(self, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback opportunities for demo reliability"""
        logger.info("🔄 Using fallback opportunity generation")

        return {
            "market_opportunities": [
                {
                    "type": "savings",
                    "title": "High-Yield Savings Upgrade",
                    "description": "Move emergency fund to high-yield savings account earning 7.5% instead of 3.5%",
                    "potential_annual_value": 18000,
                    "risk_level": "low",
                    "time_horizon": "Immediate",
                    "action_steps": ["Research high-yield accounts", "Compare rates", "Transfer funds"],
                    "confidence": 0.95
                },
                {
                    "type": "investment",
                    "title": "SIP Optimization",
                    "description": "Increase monthly SIP by ₹5,000 for better wealth creation",
                    "potential_annual_value": 60000,
                    "risk_level": "medium",
                    "time_horizon": "Long-term (5+ years)",
                    "action_steps": ["Review portfolio allocation", "Increase SIP amount", "Monitor performance"],
                    "confidence": 0.8
                }
            ],
            "market_context": {
                "current_trends": ["Rising interest rates", "Digital banking growth"],
                "risk_factors": ["Inflation pressure", "Market volatility"],
                "timing_analysis": "Good time to optimize savings allocation"
            },
            "ai_confidence": 0.7,
            "fallback_mode": True
        }

    def _generate_fallback_decision_analysis(self, decision_request) -> Dict[str, Any]:
        """Fallback decision analysis"""
        logger.info("🔄 Using fallback decision analysis")

        # Simple rule-based scoring
        base_score = 50
        amount = decision_request.amount
        category = decision_request.category.lower()

        # Adjust score based on category
        if category in ["investment", "education", "health", "insurance"]:
            base_score += 20
        elif category in ["entertainment", "luxury", "gaming"]:
            base_score -= 20

        # Adjust score based on amount
        if amount > 100000:  # > 1L
            base_score -= 15
        elif amount < 10000:  # < 10K
            base_score += 10

        final_score = max(0, min(100, base_score))

        return {
            "score": final_score,
            "explanation": f"Based on the {category} category and amount of ₹{amount:,}, this decision scores {final_score}/100. Consider the opportunity cost and alignment with your financial goals.",
            "alternatives": [
                {
                    "option": "Delay purchase by 3 months and save cash",
                    "score": min(100, final_score + 15),
                    "reasoning": "Paying cash instead of credit reduces financial stress"
                }
            ],
            "projections": {
                "net_worth_impact_1_year": -amount * 0.1,
                "net_worth_impact_5_years": -amount * 0.5,
                "opportunity_cost_5_years": amount * 1.5
            },
            "confidence": 0.6,
            "fallback_mode": True
        }

    def _create_financial_summary(self, user_data: Dict[str, Any]) -> str:
        """Create concise financial summary for AI context"""
        accounts = user_data.get("accounts", {})
        investments = user_data.get("investments", {})
        profile = user_data.get("profile", {})

        net_worth = sum(accounts.values()) + sum(investments.values()) - accounts.get("credit_used", 0)

        return f"""
        Net Worth: ₹{net_worth:,}
        Monthly Income: ₹{profile.get('income', 0) / 12:,.0f}
        Savings: ₹{accounts.get('savings', 0):,}
        Investments: ₹{sum(investments.values()):,}
        Credit Used: ₹{accounts.get('credit_used', 0):,}
        Age: {profile.get('age', 'unknown')}
        Risk Tolerance: {profile.get('risk_tolerance', 'moderate')}
        """
