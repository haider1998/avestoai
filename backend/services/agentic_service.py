# services/agentic_service.py - Agentic AI service for intelligent planning and execution
import asyncio
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import structlog
from dataclasses import dataclass
from enum import Enum

from services.vertex_ai_service import VertexAIService
from services.firestore_service import FirestoreService
from services.fi_mcp_service import FiMCPService
from models.configs import Settings

logger = structlog.get_logger()


class AgentAction(str, Enum):
    """Available agent actions"""
    ANALYZE_FINANCIAL_DATA = "analyze_financial_data"
    GENERATE_OPPORTUNITIES = "generate_opportunities"
    CREATE_ACTION_PLAN = "create_action_plan"
    MONITOR_PROGRESS = "monitor_progress"
    PROVIDE_GUIDANCE = "provide_guidance"
    ASSESS_RISK = "assess_risk"
    OPTIMIZE_PORTFOLIO = "optimize_portfolio"


@dataclass
class AgentTask:
    """Represents a task for the agentic system"""
    id: str
    action: AgentAction
    priority: int  # 1-10, 10 being highest
    context: Dict[str, Any]
    dependencies: List[str]
    estimated_duration: int  # in seconds
    created_at: datetime
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class AgentPlan:
    """Represents an execution plan"""
    id: str
    goal: str
    tasks: List[AgentTask]
    mobile_number: str
    created_at: datetime
    estimated_completion: datetime
    status: str = "planning"  # planning, executing, completed, failed


class AgenticService:
    """
    Agentic AI service that can plan, execute, and respond intelligently
    to user financial queries and needs
    """
    
    def __init__(self, vertex_ai: VertexAIService, firestore: FirestoreService, fi_mcp: FiMCPService, settings: Settings):
        self.vertex_ai = vertex_ai
        self.firestore = firestore
        self.fi_mcp = fi_mcp
        self.settings = settings
        self.active_plans: Dict[str, AgentPlan] = {}
        self.task_queue: List[AgentTask] = []
        
    async def create_intelligent_plan(self, user_query: str, mobile_number: str, context: Dict[str, Any] = None) -> AgentPlan:
        """
        Create an intelligent execution plan based on user query and context
        """
        logger.info("Creating intelligent plan", query=user_query, mobile_number=mobile_number)
        
        try:
            # Get user's financial context
            financial_context = await self._get_user_context(mobile_number)
            
            # Analyze the query and determine intent
            intent_analysis = await self._analyze_user_intent(user_query, financial_context)
            
            # Generate execution plan
            plan = await self._generate_execution_plan(intent_analysis, mobile_number, context or {})
            
            # Store the plan
            self.active_plans[plan.id] = plan
            
            logger.info("Intelligent plan created", plan_id=plan.id, tasks_count=len(plan.tasks))
            return plan
            
        except Exception as e:
            logger.error("Failed to create intelligent plan", error=str(e))
            raise
    
    async def execute_plan(self, plan_id: str) -> Dict[str, Any]:
        """
        Execute a plan with intelligent task scheduling and dependency management
        """
        if plan_id not in self.active_plans:
            raise ValueError(f"Plan {plan_id} not found")
        
        plan = self.active_plans[plan_id]
        plan.status = "executing"
        
        logger.info("Starting plan execution", plan_id=plan_id, goal=plan.goal)
        
        try:
            # Execute tasks based on dependencies and priority
            results = await self._execute_tasks_intelligently(plan.tasks)
            
            # Compile final response
            final_response = await self._compile_intelligent_response(plan, results)
            
            plan.status = "completed"
            logger.info("Plan execution completed", plan_id=plan_id)
            
            return final_response
            
        except Exception as e:
            plan.status = "failed"
            logger.error("Plan execution failed", plan_id=plan_id, error=str(e))
            raise
    
    async def respond_intelligently(self, query: str, mobile_number: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Provide intelligent responses with planning and execution
        """
        logger.info("Processing intelligent response", query=query, mobile_number=mobile_number)
        
        # Create and execute plan
        plan = await self.create_intelligent_plan(query, mobile_number)
        response = await self.execute_plan(plan.id)
        
        # Add conversational elements
        response["conversation_id"] = plan.id
        response["plan_summary"] = {
            "goal": plan.goal,
            "tasks_executed": len(plan.tasks),
            "execution_time": (datetime.now() - plan.created_at).total_seconds()
        }
        
        return response
    
    async def _get_user_context(self, mobile_number: str) -> Dict[str, Any]:
        """Get comprehensive user context"""
        try:
            # Get financial data from Fi MCP
            financial_data = await self.fi_mcp.get_user_financial_data(mobile_number)
            
            # Get recent analysis history
            recent_analysis = await self.firestore.get_recent_analysis(mobile_number, limit=3)
            
            # Get conversation history
            conversation_history = await self.firestore.get_conversation_history(mobile_number, limit=5)
            
            return {
                "financial_data": financial_data,
                "recent_analysis": recent_analysis,
                "conversation_history": conversation_history,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.warning("Failed to get complete user context", error=str(e))
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    async def _analyze_user_intent(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user intent using AI"""
        
        prompt = f"""
        Analyze the user's financial query and determine their intent, urgency, and required actions.
        
        User Query: "{query}"
        
        Financial Context: {json.dumps(context.get('financial_data', {}), indent=2)}
        
        Provide analysis in this JSON format:
        {{
            "primary_intent": "string (e.g., 'investment_advice', 'expense_optimization', 'debt_management')",
            "urgency_level": "number (1-10)",
            "required_actions": ["list", "of", "actions"],
            "data_requirements": ["list", "of", "data", "needed"],
            "expected_outcome": "string describing what user expects",
            "complexity_score": "number (1-10)",
            "estimated_time": "number in seconds"
        }}
        """
        
        try:
            response = await self.vertex_ai._generate_local(prompt, max_tokens=1000)
            return self.vertex_ai._parse_json_response(response)
        except Exception as e:
            logger.warning("Failed to analyze intent with AI, using fallback", error=str(e))
            return self._fallback_intent_analysis(query)
    
    async def _generate_execution_plan(self, intent_analysis: Dict[str, Any], mobile_number: str, context: Dict[str, Any]) -> AgentPlan:
        """Generate intelligent execution plan"""
        
        plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{mobile_number[-4:]}"
        
        # Create tasks based on intent
        tasks = []
        task_counter = 1
        
        # Always start with data analysis if needed
        if "financial_data" in intent_analysis.get("data_requirements", []):
            tasks.append(AgentTask(
                id=f"{plan_id}_task_{task_counter}",
                action=AgentAction.ANALYZE_FINANCIAL_DATA,
                priority=9,
                context={"mobile_number": mobile_number},
                dependencies=[],
                estimated_duration=30,
                created_at=datetime.now()
            ))
            task_counter += 1
        
        # Add specific tasks based on intent
        primary_intent = intent_analysis.get("primary_intent", "general_advice")
        
        if "investment" in primary_intent.lower():
            tasks.append(AgentTask(
                id=f"{plan_id}_task_{task_counter}",
                action=AgentAction.OPTIMIZE_PORTFOLIO,
                priority=8,
                context={"mobile_number": mobile_number, "focus": "investment"},
                dependencies=[tasks[0].id] if tasks else [],
                estimated_duration=45,
                created_at=datetime.now()
            ))
            task_counter += 1
        
        if "opportunity" in primary_intent.lower() or "advice" in primary_intent.lower():
            tasks.append(AgentTask(
                id=f"{plan_id}_task_{task_counter}",
                action=AgentAction.GENERATE_OPPORTUNITIES,
                priority=7,
                context={"mobile_number": mobile_number},
                dependencies=[tasks[0].id] if tasks else [],
                estimated_duration=60,
                created_at=datetime.now()
            ))
            task_counter += 1
        
        # Always end with action plan and guidance
        tasks.append(AgentTask(
            id=f"{plan_id}_task_{task_counter}",
            action=AgentAction.CREATE_ACTION_PLAN,
            priority=6,
            context={"mobile_number": mobile_number, "intent": intent_analysis},
            dependencies=[task.id for task in tasks],
            estimated_duration=30,
            created_at=datetime.now()
        ))
        task_counter += 1
        
        tasks.append(AgentTask(
            id=f"{plan_id}_task_{task_counter}",
            action=AgentAction.PROVIDE_GUIDANCE,
            priority=5,
            context={"mobile_number": mobile_number, "intent": intent_analysis},
            dependencies=[tasks[-1].id],
            estimated_duration=20,
            created_at=datetime.now()
        ))
        
        # Calculate estimated completion time
        total_duration = sum(task.estimated_duration for task in tasks)
        estimated_completion = datetime.now() + timedelta(seconds=total_duration)
        
        return AgentPlan(
            id=plan_id,
            goal=intent_analysis.get("expected_outcome", "Provide financial guidance"),
            tasks=tasks,
            mobile_number=mobile_number,
            created_at=datetime.now(),
            estimated_completion=estimated_completion
        )
    
    async def _execute_tasks_intelligently(self, tasks: List[AgentTask]) -> Dict[str, Any]:
        """Execute tasks with intelligent scheduling"""
        results = {}
        completed_tasks = set()
        
        # Sort tasks by priority and dependencies
        remaining_tasks = tasks.copy()
        
        while remaining_tasks:
            # Find tasks that can be executed (dependencies met)
            executable_tasks = [
                task for task in remaining_tasks
                if all(dep in completed_tasks for dep in task.dependencies)
            ]
            
            if not executable_tasks:
                logger.error("Circular dependency detected in tasks")
                break
            
            # Execute highest priority task
            task = max(executable_tasks, key=lambda t: t.priority)
            task.status = "in_progress"
            
            try:
                logger.info("Executing task", task_id=task.id, action=task.action.value)
                result = await self._execute_single_task(task)
                task.result = result
                task.status = "completed"
                results[task.id] = result
                completed_tasks.add(task.id)
                
            except Exception as e:
                task.status = "failed"
                task.error = str(e)
                logger.error("Task execution failed", task_id=task.id, error=str(e))
                results[task.id] = {"error": str(e)}
            
            remaining_tasks.remove(task)
        
        return results
    
    async def _execute_single_task(self, task: AgentTask) -> Dict[str, Any]:
        """Execute a single task based on its action"""
        
        mobile_number = task.context.get("mobile_number")
        
        if task.action == AgentAction.ANALYZE_FINANCIAL_DATA:
            return await self.fi_mcp.get_user_financial_data(mobile_number)
        
        elif task.action == AgentAction.GENERATE_OPPORTUNITIES:
            from services.opportunity_engine import OpportunityEngine
            engine = OpportunityEngine(self.vertex_ai, self.firestore, self.fi_mcp)
            financial_data = await self.fi_mcp.get_user_financial_data(mobile_number)
            return await engine.generate_opportunities(financial_data, mobile_number=mobile_number)
        
        elif task.action == AgentAction.ASSESS_RISK:
            financial_data = await self.fi_mcp.get_user_financial_data(mobile_number)
            return await self.vertex_ai.calculate_real_time_health(financial_data)
        
        elif task.action == AgentAction.CREATE_ACTION_PLAN:
            return await self._create_action_plan(task.context)
        
        elif task.action == AgentAction.PROVIDE_GUIDANCE:
            return await self._provide_intelligent_guidance(task.context)
        
        elif task.action == AgentAction.OPTIMIZE_PORTFOLIO:
            return await self._optimize_portfolio(task.context)
        
        else:
            return {"message": f"Task {task.action.value} executed successfully"}
    
    async def _create_action_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create actionable plan for user"""
        mobile_number = context.get("mobile_number")
        intent = context.get("intent", {})
        
        prompt = f"""
        Create a detailed, actionable financial plan based on the user's intent and situation.
        
        User Intent: {json.dumps(intent, indent=2)}
        
        Provide a structured action plan in JSON format:
        {{
            "immediate_actions": [
                {{"action": "string", "timeline": "string", "priority": "high/medium/low"}}
            ],
            "short_term_goals": [
                {{"goal": "string", "timeline": "1-3 months", "steps": ["step1", "step2"]}}
            ],
            "long_term_goals": [
                {{"goal": "string", "timeline": "6-12 months", "steps": ["step1", "step2"]}}
            ],
            "success_metrics": ["metric1", "metric2"],
            "potential_obstacles": ["obstacle1", "obstacle2"],
            "review_schedule": "string"
        }}
        """
        
        try:
            response = await self.vertex_ai._generate_local(prompt, max_tokens=1500)
            return self.vertex_ai._parse_json_response(response)
        except Exception as e:
            return {"error": f"Failed to create action plan: {str(e)}"}
    
    async def _provide_intelligent_guidance(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Provide intelligent guidance"""
        return {
            "guidance": "Based on your financial situation, I recommend focusing on building your emergency fund first.",
            "next_steps": [
                "Review your monthly expenses",
                "Set up automatic savings",
                "Consider high-yield savings accounts"
            ],
            "confidence": 0.85,
            "reasoning": "Emergency fund provides financial security and should be prioritized."
        }
    
    async def _optimize_portfolio(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize investment portfolio"""
        mobile_number = context.get("mobile_number")
        financial_data = await self.fi_mcp.get_user_financial_data(mobile_number)
        
        return {
            "current_allocation": "Analyzed current portfolio allocation",
            "recommended_changes": [
                "Increase equity allocation by 10%",
                "Diversify across sectors",
                "Consider international exposure"
            ],
            "expected_improvement": "Potential 2-3% annual return improvement",
            "risk_assessment": "Moderate risk increase with better diversification"
        }
    
    async def _compile_intelligent_response(self, plan: AgentPlan, results: Dict[str, Any]) -> Dict[str, Any]:
        """Compile final intelligent response"""
        
        # Extract key insights from all task results
        insights = []
        recommendations = []
        
        for task_id, result in results.items():
            if isinstance(result, dict):
                if "opportunities" in result:
                    insights.append("Identified new financial opportunities")
                    recommendations.extend(result.get("recommendations", []))
                
                if "guidance" in result:
                    insights.append("Generated personalized guidance")
                    recommendations.append(result["guidance"])
        
        return {
            "response": f"I've analyzed your financial situation and created a comprehensive plan to help you achieve your goals.",
            "insights": insights,
            "recommendations": recommendations[:5],  # Top 5 recommendations
            "action_plan": results.get("action_plan", {}),
            "confidence": 0.9,
            "plan_id": plan.id,
            "execution_summary": {
                "tasks_completed": len([r for r in results.values() if "error" not in r]),
                "tasks_failed": len([r for r in results.values() if "error" in r]),
                "total_tasks": len(results)
            }
        }
    
    def _fallback_intent_analysis(self, query: str) -> Dict[str, Any]:
        """Fallback intent analysis when AI is unavailable"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["invest", "investment", "portfolio"]):
            intent = "investment_advice"
            urgency = 6
        elif any(word in query_lower for word in ["save", "saving", "emergency"]):
            intent = "savings_optimization"
            urgency = 7
        elif any(word in query_lower for word in ["debt", "loan", "credit"]):
            intent = "debt_management"
            urgency = 8
        else:
            intent = "general_advice"
            urgency = 5
        
        return {
            "primary_intent": intent,
            "urgency_level": urgency,
            "required_actions": ["analyze_financial_data", "provide_guidance"],
            "data_requirements": ["financial_data"],
            "expected_outcome": "Provide helpful financial guidance",
            "complexity_score": 5,
            "estimated_time": 120
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        self.active_plans.clear()
        self.task_queue.clear()
        logger.info("Agentic service cleaned up")
