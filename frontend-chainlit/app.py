# frontend-chainlit/app.py
import chainlit as cl
import httpx
import json
import asyncio
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
API_TIMEOUT = 30

# Global variables
user_token = None
user_profile = None


@cl.password_auth_callback
def auth_callback(username: str, password: str):
    """Handle user authentication"""
    # This would normally validate against your user database
    # For demo purposes, we'll use a simple check
    if username == "demo@avestoai.com" and password == "demo123":
        return cl.User(
            identifier="demo_user",
            metadata={"role": "user", "provider": "credentials"}
        )
    return None


@cl.on_chat_start
async def start():
    """Initialize chat session"""
    global user_token, user_profile

    # Welcome message
    await cl.Message(
        content="🔮 **Welcome to AvestoAI - Your Financial Prophet!**\n\n"
                "I'm your AI financial advisor powered by Google's Gemini AI and real-time data from Fi Money.\n\n"
                "**What I can help you with:**\n"
                "💡 **Discover hidden opportunities** in your finances\n"
                "🎯 **Score financial decisions** before you make them\n"
                "📈 **Track your financial health** in real-time\n"
                "⚠️ **Predict potential problems** 7-30 days ahead\n"
                "🏆 **Optimize your wealth building** strategy\n\n"
                "Let me start by getting your financial dashboard...",
        author="AvestoAI"
    ).send()

    # Try to authenticate and get user data
    try:
        # For demo, we'll use a sample user
        await authenticate_demo_user()
        await show_financial_dashboard()
    except Exception as e:
        await cl.Message(
            content=f"⚠️ **Demo Mode Active**\n\n"
                    f"I'm running in demo mode with sample financial data. "
                    f"All analysis and recommendations are based on realistic demo data.\n\n"
                    f"You can still explore all features including:\n"
                    f"- Financial opportunity analysis\n"
                    f"- Decision scoring\n"
                    f"- Predictive insights\n"
                    f"- Real-time health monitoring\n\n"
                    f"Try asking: *\"What opportunities do you see in my finances?\"*",
            author="AvestoAI"
        ).send()


async def authenticate_demo_user():
    """Authenticate demo user and get token"""
    global user_token, user_profile

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            # Try to login with demo credentials
            login_response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/login",
                json={
                    "email": "demo@avestoai.com",
                    "password": "demo123"
                }
            )

            if login_response.status_code == 200:
                auth_data = login_response.json()
                user_token = auth_data["access_token"]
                user_profile = auth_data["user"]
            else:
                # Register demo user if doesn't exist
                register_response = await client.post(
                    f"{API_BASE_URL}/api/v1/auth/register",
                    json={
                        "email": "demo@avestoai.com",
                        "password": "demo123",
                        "name": "Demo User",
                        "age": 28,
                        "city": "Bangalore",
                        "annual_income": 1200000,
                        "risk_tolerance": "moderate"
                    }
                )

                if register_response.status_code == 200:
                    auth_data = register_response.json()
                    user_token = auth_data["access_token"]
                    user_profile = auth_data["user"]

    except Exception as e:
        print(f"Authentication failed: {e}")
        # Continue in demo mode without real authentication


@cl.on_message
async def main(message: cl.Message):
    """Handle user messages"""

    user_input = message.content.lower()

    # Route different types of queries
    if any(word in user_input for word in ["opportunity", "opportunities", "optimize", "save money", "improve"]):
        await handle_opportunity_request(message.content)

    elif any(word in user_input for word in ["should i buy", "purchase", "decision", "score", "worth buying"]):
        await handle_decision_scoring(message.content)

    elif any(word in user_input for word in ["health", "score", "status", "dashboard", "overview"]):
        await show_financial_dashboard()

    elif any(word in user_input for word in ["predict", "future", "forecast", "timeline", "projection"]):
        await handle_prediction_request(message.content)

    elif any(word in user_input for word in ["alert", "warning", "risk", "problem"]):
        await handle_risk_analysis()

    elif any(word in user_input for word in ["goal", "goals", "target", "planning"]):
        await handle_goal_planning(message.content)

    else:
        await handle_general_query(message.content)


async def show_financial_dashboard():
    """Display comprehensive financial dashboard"""

    try:
        headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            # Get dashboard data
            dashboard_response = await client.get(
                f"{API_BASE_URL}/api/v1/financial-dashboard/demo_user",
                headers=headers
            )

            if dashboard_response.status_code == 200:
                dashboard_data = dashboard_response.json()
                await display_dashboard_data(dashboard_data)
            else:
                await display_demo_dashboard()

    except Exception as e:
        await display_demo_dashboard()


async def display_dashboard_data(dashboard_data: Dict):
    """Display dashboard with real data"""

    summary = dashboard_data.get("financial_summary", {})
    health_score = dashboard_data.get("health_score", 75)
    insights = dashboard_data.get("insights", [])

    # Create health score gauge
    health_chart = create_health_score_gauge(health_score)

    # Create net worth chart
    net_worth_chart = create_net_worth_breakdown(summary)

    # Format dashboard message
    content = f"📊 **Your Financial Dashboard**\n\n"
    content += f"💰 **Net Worth**: ₹{summary.get('net_worth', 0):,.0f}\n"
    content += f"💵 **Liquid Assets**: ₹{summary.get('liquid_assets', 0):,.0f}\n"
    content += f"📈 **Investments**: ₹{summary.get('investments', 0):,.0f}\n"
    content += f"💳 **Debt**: ₹{summary.get('debt', 0):,.0f}\n"
    content += f"💸 **Monthly Cash Flow**: ₹{summary.get('monthly_income', 0) - summary.get('monthly_expenses', 0):,.0f}\n"
    content += f"🛡️ **Emergency Fund**: {summary.get('emergency_fund_months', 0):.1f} months\n\n"

    content += f"🏥 **Financial Health Score**: {health_score}/100\n\n"

    if insights:
        content += "💡 **Key Insights**:\n"
        for insight in insights[:3]:
            content += f"• {insight}\n"
        content += "\n"

    content += "🔍 **Want to explore more?** Ask me:\n"
    content += "• *\"What opportunities do you see?\"*\n"
    content += "• *\"Should I buy a laptop for ₹80,000?\"*\n"
    content += "• *\"What's my financial future looking like?\"*"

    elements = [
        cl.Plotly(name="health_score", figure=health_chart, display="inline"),
        cl.Plotly(name="net_worth", figure=net_worth_chart, display="inline")
    ]

    await cl.Message(
        content=content,
        elements=elements
    ).send()


async def display_demo_dashboard():
    """Display demo dashboard"""

    # Create demo charts
    health_chart = create_health_score_gauge(78)
    net_worth_chart = create_demo_net_worth_chart()

    content = """📊 **Your Financial Dashboard (Demo Data)**

💰 **Net Worth**: ₹9.1 Lakhs
💵 **Liquid Assets**: ₹2.95 Lakhs  
📈 **Investments**: ₹6.3 Lakhs
💳 **Debt**: ₹35,000
💸 **Monthly Cash Flow**: ₹45,000
🛡️ **Emergency Fund**: 3.9 months

🏥 **Financial Health Score**: 78/100

💡 **Key Insights**:
• Your net worth increased by ₹45,000 this month - excellent progress!
• Consider moving ₹50,000 to high-yield investments for better returns
• Emergency fund is strong, but could be optimized for higher yield

🔍 **Explore More**:
• *"What opportunities do you see in my finances?"*
• *"Should I buy a MacBook for ₹150,000?"*
• *"Show me my wealth projection for next 5 years"*"""

    elements = [
        cl.Plotly(name="health_score", figure=health_chart, display="inline"),
        cl.Plotly(name="net_worth", figure=net_worth_chart, display="inline")
    ]

    await cl.Message(
        content=content,
        elements=elements
    ).send()


async def handle_opportunity_request(user_message: str):
    """Handle requests for financial opportunities"""

    await cl.Message(
        content="🔍 **Analyzing your financial data for opportunities...**\n\nThis may take a few seconds as I examine your accounts, spending patterns, and market conditions.",
        author="AvestoAI").send()

    try:
        headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/analyze-opportunities",
                json={
                    "analysis_type": "comprehensive",
                    "include_predictions": True,
                    "time_horizon": "1_year"
                },
                headers=headers
            )

            if response.status_code == 200:
                opportunities_data = response.json()
                await display_opportunities(opportunities_data)
            else:
                await display_demo_opportunities()

    except Exception as e:
        await display_demo_opportunities()


async def display_opportunities(opportunities_data: Dict):
    """Display opportunities from API"""

    opportunities = opportunities_data.get("opportunities", [])
    total_value = opportunities_data.get("total_annual_value", 0)

    if not opportunities:
        await cl.Message(
            content="🎉 **Great news!** Your finances are well-optimized. I couldn't find any major improvement opportunities right now.\n\nKeep up the excellent financial discipline!",
            author="AvestoAI"
        ).send()
        return

    content = f"💡 **Financial Opportunities Detected**\n\n"
    content += f"🎯 **Total Annual Impact**: ₹{total_value:,.0f}\n\n"

    for i, opp in enumerate(opportunities[:3], 1):
        priority_emoji = "🔥" if opp.get("priority") == "high" else "⭐" if opp.get("priority") == "medium" else "💡"

        content += f"{priority_emoji} **{opp.get('title', 'Opportunity')}**\n"
        content += f"   💰 **Annual Value**: ₹{opp.get('potential_annual_value', 0):,.0f}\n"
        content += f"   ⏱️ **Effort**: {opp.get('effort_level', 'Medium')} | **Time**: {opp.get('time_to_implement', 'TBD')}\n"
        content += f"   🎯 **Confidence**: {opp.get('confidence_score', 0.8) * 100:.0f}%\n"
        content += f"   📝 {opp.get('description', 'No description available')}\n\n"

    if len(opportunities) > 3:
        content += f"*...and {len(opportunities) - 3} more opportunities*\n\n"

    content += "💬 **Want details?** Ask me:\n"
    content += "• *\"How do I implement the savings optimization?\"*\n"
    content += "• *\"Show me the investment opportunity details\"*\n"
    content += "• *\"What are the risks of these opportunities?\"*"

    await cl.Message(content=content, author="AvestoAI").send()


async def display_demo_opportunities():
    """Display demo opportunities"""

    content = """💡 **Financial Opportunities Detected**

🎯 **Total Annual Impact**: ₹45,200

🔥 **High-Yield Savings Optimization**
   💰 **Annual Value**: ₹18,200
   ⏱️ **Effort**: Low | **Time**: 1 day
   🎯 **Confidence**: 95%
   📝 Move ₹2.5L to high-yield savings earning 7.2% instead of 3.5%

⭐ **SIP Investment Increase** 
   💰 **Annual Value**: ₹20,000
   ⏱️ **Effort**: Low | **Time**: 1 week  
   🎯 **Confidence**: 88%
   📝 Increase monthly SIP by ₹3,000 for better long-term wealth creation

💡 **Dining Expense Optimization**
   💰 **Annual Value**: ₹7,000
   ⏱️ **Effort**: Medium | **Time**: 1 month
   🎯 **Confidence**: 75%
   📝 Optimize food delivery spending with meal planning and cooking

💬 **Want to implement these?** Ask me:
• *"How do I move to high-yield savings?"*
• *"Which SIP funds should I choose?"*
• *"Give me a meal planning strategy"*"""

    await cl.Message(content=content, author="AvestoAI").send()


async def handle_decision_scoring(user_message: str):
    """Handle financial decision scoring requests"""

    # Try to extract amount and item from message
    import re
    amount_match = re.search(r'₹?(\d+(?:,\d+)*(?:\.\d+)?)', user_message)

    if amount_match:
        amount = int(amount_match.group(1).replace(',', ''))
        await score_financial_decision(user_message, amount)
    else:
        # Ask for clarification
        await cl.Message(
            content="🎯 **Decision Scorer**\n\nI'd be happy to analyze any financial decision for you!\n\nPlease tell me:\n1. What are you considering buying/investing in?\n2. How much does it cost?\n\nFor example: *\"Should I buy a MacBook Pro for ₹150,000?\"*",
            author="AvestoAI"
        ).send()


async def score_financial_decision(description: str, amount: int):
    """Score a specific financial decision"""

    await cl.Message(
        content=f"🎯 **Analyzing your decision...**\n\n**Purchase**: {description}\n**Amount**: ₹{amount:,}\n\nLet me evaluate this against your financial goals and current situation...",
        author="AvestoAI"
    ).send()

    try:
        headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}

        # Determine category from description
        category = determine_category(description)

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/predict-decision",
                json={
                    "amount": amount,
                    "category": category,
                    "description": description,
                    "financing_method": "cash",
                    "user_context": {
                        "current_savings": 295000,
                        "monthly_income": 120000,
                        "investment_value": 630000
                    }
                },
                headers=headers
            )

            if response.status_code == 200:
                decision_data = response.json()
                await display_decision_analysis(decision_data, amount, description)
            else:
                await display_demo_decision_analysis(amount, category, description)

    except Exception as e:
        await display_demo_decision_analysis(amount, "electronics", description)


async def display_decision_analysis(decision_data: Dict, amount: int, description: str):
    """Display decision analysis results"""

    score = decision_data.get("score", 65)
    explanation = decision_data.get("explanation", "Analysis completed")
    alternatives = decision_data.get("alternatives", [])
    long_term_impact = decision_data.get("long_term_impact", {})

    # Create score visualization
    score_chart = create_decision_score_gauge(score, amount)

    # Determine score interpretation
    if score >= 80:
        score_emoji = "🟢"
        score_text = "Excellent Decision"
        score_color = "green"
    elif score >= 60:
        score_emoji = "🟡"
        score_text = "Good Decision"
        score_color = "orange"
    else:
        score_emoji = "🔴"
        score_text = "Consider Alternatives"
        score_color = "red"

    content = f"🎯 **Financial Decision Analysis**\n\n"
    content += f"**Purchase**: {description}\n"
    content += f"**Amount**: ₹{amount:,}\n\n"
    content += f"{score_emoji} **Score**: {score}/100 - {score_text}\n\n"
    content += f"**Analysis**: {explanation}\n\n"

    if long_term_impact:
        content += "📈 **Long-term Impact**:\n"
        if "net_worth_impact_5_years" in long_term_impact:
            impact = long_term_impact["net_worth_impact_5_years"]
            content += f"• 5-year net worth impact: ₹{impact:,.0f}\n"
        if "opportunity_cost_5_years" in long_term_impact:
            opp_cost = long_term_impact["opportunity_cost_5_years"]
            content += f"• Opportunity cost if invested: ₹{opp_cost:,.0f}\n"
        content += "\n"

    if alternatives:
        content += "💡 **Better Alternatives**:\n"
        for alt in alternatives[:2]:
            content += f"• {alt.get('option', 'Alternative option')} (Score: {alt.get('score', 70)}/100)\n"
        content += "\n"

    content += "💬 **Questions?** Ask me:\n"
    content += "• *\"What if I wait 3 months to buy this?\"*\n"
    content += "• *\"Show me better alternatives\"*\n"
    content += "• *\"How does this affect my goals?\"*"

    await cl.Message(
        content=content,
        elements=[cl.Plotly(name="decision_score", figure=score_chart, display="inline")]
    ).send()


async def display_demo_decision_analysis(amount: int, category: str, description: str):
    """Display demo decision analysis"""

    # Simple scoring logic for demo
    base_score = 60
    if category in ["education", "health", "investment"]:
        base_score += 20
    elif category in ["entertainment", "luxury"]:
        base_score -= 15

    if amount > 100000:
        base_score -= 10
    elif amount < 20000:
        base_score += 10

    score = max(20, min(95, base_score))

    score_chart = create_decision_score_gauge(score, amount)

    if score >= 75:
        score_emoji = "🟢"
        score_text = "Good Decision"
        analysis = f"This {category} purchase aligns well with your financial goals. You have sufficient cash flow to afford it without compromising your emergency fund."
    elif score >= 50:
        score_emoji = "🟡"
        score_text = "Consider Carefully"
        analysis = f"This {category} purchase is feasible but consider the opportunity cost. Investing this amount could yield ₹{amount * 1.6:,.0f} in 5 years."
    else:
        score_emoji = "🔴"
        score_text = "Reconsider"
        analysis = f"This {category} purchase may strain your finances. Consider waiting or exploring alternatives."

    content = f"""🎯 **Financial Decision Analysis**

**Purchase**: {description}
**Amount**: ₹{amount:,}

{score_emoji} **Score**: {score}/100 - {score_text}

**Analysis**: {analysis}

📈 **Long-term Impact**:
• 5-year opportunity cost if invested: ₹{amount * 1.6:,.0f}
• Impact on emergency fund: Minimal
• Effect on financial goals: {['Delayed', 'Minimal', 'Positive'][score // 35]}

💡 **Recommendation**: {"Proceed with purchase" if score >= 70 else "Consider waiting 2-3 months" if score >= 50 else "Explore alternatives or wait 6 months"}

💬 **Want to explore more?**
• *"What if I finance this instead of paying cash?"*
• *"Show me the impact on my retirement planning"*
• *"What are some alternatives?"*"""

    await cl.Message(
        content=content,
        elements=[cl.Plotly(name="decision_score", figure=score_chart, display="inline")]
    ).send()


async def handle_prediction_request(user_message: str):
    """Handle future prediction requests"""

    wealth_chart = create_wealth_projection_chart()
    goals_chart = create_goals_progress_chart()

    content = """🔮 **Your Financial Future Prediction**

📈 **Wealth Trajectory (Next 10 Years)**:
• **Year 1**: ₹12.3 Lakhs (+35%)
• **Year 3**: ₹22.8 Lakhs (+151%) 
• **Year 5**: ₹41.2 Lakhs (+353%)
• **Year 10**: ₹1.15 Crores (+1,164%)

🎯 **Key Milestones**:
• **Emergency Fund Goal** (₹6L): ✅ Achieved
• **House Down Payment** (₹20L): 2.3 years
• **Financial Independence**: Age 38 (10 years)
• **Retirement Corpus** (₹5Cr): Age 45

⚡ **Acceleration Opportunities**:
• Increase SIP by ₹5K → Retire 18 months earlier
• Optimize high-yield savings → +₹18K annually  
• Tax planning optimization → +₹45K annually

🎲 **Scenarios**:
• **Conservative** (8% returns): ₹85L in 10 years
• **Moderate** (12% returns): ₹1.15Cr in 10 years
• **Aggressive** (15% returns): ₹1.55Cr in 10 years

⚠️ **Predicted Challenges**:
• Month 8: Potential cashflow squeeze during festival season
• Year 2: EMI increase due to rate hikes
• Year 5: Child education expenses begin

💪 **Success Factors**:
• Consistent SIP investments: 85% wealth growth
• Emergency fund maintenance: Risk mitigation
• Expense discipline: 23% of wealth protection"""

    elements = [
        cl.Plotly(name="wealth_projection", figure=wealth_chart, display="inline"),
        cl.Plotly(name="goals_progress", figure=goals_chart, display="inline")
    ]

    await cl.Message(
        content=content,
        elements=elements
    ).send()


async def handle_risk_analysis():
    """Handle risk and alert analysis"""

    risk_chart = create_risk_analysis_chart()

    content = """⚠️ **Smart Risk Analysis & Alerts**

🔍 **Current Risk Assessment**: **Medium-Low**

📊 **Risk Breakdown**:
• **Liquidity Risk**: Low (3.9 months emergency fund)
• **Market Risk**: Medium (70% equity allocation)
• **Inflation Risk**: Medium (4.2% current inflation)
• **Income Risk**: Low (stable job, growing income)
• **Debt Risk**: Very Low (3.5% debt-to-income ratio)

📅 **Predictive Alerts (Next 30 Days)**:
• **Day 8**: Festival expenses likely to spike 40%
• **Day 15**: Credit card payment due (₹25,000)
• **Day 22**: Mutual fund SIP deduction (₹15,000)
• **Day 28**: Salary credit expected

🚨 **Attention Required**:
• Insurance coverage review due (last updated 18 months ago)
• Credit score monitoring (currently 750+)
• Investment rebalancing needed (equity at 72% vs target 70%)

🛡️ **Risk Mitigation Strategies**:
1. **Diversify Investments**: Add 5% international exposure
2. **Insurance Optimization**: Increase term life cover by ₹50L
3. **Emergency Fund**: Move to higher-yield account for better returns
4. **Credit Management**: Set up automatic payments to avoid delays

🎯 **Opportunity in Crisis**:
• Market correction in IT sector: Buying opportunity in next 3 months
• Interest rate peak expected: Good time for debt mutual funds
• Real estate prices softening: Consider REIT investments

💡 **Monitoring Dashboard**:
• Daily spending velocity: Currently 12% above average
• Investment performance: Beating benchmark by 2.3%
• Goal timeline: On track for all major milestones"""

    await cl.Message(
        content=content,
        elements=[cl.Plotly(name="risk_analysis", figure=risk_chart, display="inline")]
    ).send()


async def handle_goal_planning(user_message: str):
    """Handle financial goal planning"""

    goals_timeline_chart = create_goals_timeline_chart()

    content = """🎯 **Financial Goals Planning & Tracking**

📋 **Current Goals Status**:

🏠 **House Purchase Goal**
• **Target**: ₹20 Lakhs (down payment)
• **Current**: ₹8.4 Lakhs (42% complete)
• **Timeline**: 2.3 years at current rate
• **Monthly Allocation**: ₹35,000

🚨 **Emergency Fund**
• **Target**: ₹6 Lakhs (6 months expenses)  
• **Current**: ₹4.7 Lakhs (78% complete)
• **Status**: ✅ Nearly Complete
• **Action**: Move to high-yield account

👶 **Child Education Fund**
• **Target**: ₹25 Lakhs (by 2035)
• **Current**: ₹2.1 Lakhs (8% complete)
• **Monthly Needed**: ₹8,500
• **Current Allocation**: ₹5,000 (Increase needed!)

🌴 **Retirement Corpus**
• **Target**: ₹5 Crores (by age 60)
• **Current**: ₹12.5 Lakhs (2.5% complete)
• **Monthly SIP**: ₹15,000
• **Projected**: On track with 12% returns

🎯 **Goal Optimization Recommendations**:

**Priority 1: Emergency Fund** (Complete in 3 months)
• Increase allocation by ₹10,000/month
• Move to high-yield savings for better returns

**Priority 2: Child Education** (Start aggressive saving)
• Increase SIP to ₹8,500/month
• Consider Sukanya Samriddhi Yojana

**Priority 3: House Purchase** (Accelerate timeline)
• Side income opportunities could save 8 months
• Consider parents' gift/loan for faster achievement

💡 **Smart Goal Hacks**:
• Use bonus for emergency fund completion
• PPF maxing for tax + child education goal
• Real estate SIP for house down payment goal

📊 **Goal Impact Analysis**:
• Completing emergency fund → Reduces financial stress by 65%
• House purchase goal → Builds ₹15L+ equity over 10 years
• Child education fund → Ensures quality education without loans"""

    await cl.Message(
        content=content,
        elements=[cl.Plotly(name="goals_timeline", figure=goals_timeline_chart, display="inline")]
    ).send()


async def handle_general_query(user_message: str):
    """Handle general financial queries using AI chat"""

    try:
        headers = {"Authorization": f"Bearer {user_token}"} if user_token else {}

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/chat",
                json={
                    "message": user_message,
                    "include_charts": True,
                    "context_type": "general"
                },
                headers=headers
            )

            if response.status_code == 200:
                chat_data = response.json()
                await display_chat_response(chat_data)
            else:
                await display_fallback_response(user_message)

    except Exception as e:
        await display_fallback_response(user_message)


async def display_chat_response(chat_data: Dict):
    """Display AI chat response"""

    response_text = chat_data.get("response", "")
    suggestions = chat_data.get("suggestions", [])
    charts = chat_data.get("charts", [])

    content = f"💡 **AI Financial Advisor**\n\n{response_text}"

    if suggestions:
        content += "\n\n🔍 **You might also ask**:\n"
        for suggestion in suggestions[:3]:
            content += f"• *\"{suggestion}\"*\n"

    elements = []
    for chart in charts:
        if chart.get("data"):
            plotly_chart = create_chart_from_data(chart)
            elements.append(cl.Plotly(name=chart.get("title", "chart"), figure=plotly_chart, display="inline"))

    await cl.Message(
        content=content,
        elements=elements if elements else None
    ).send()


async def display_fallback_response(user_message: str):
    """Display fallback response for general queries"""

    content = """💡 **AI Financial Advisor**

I'm here to help with all your financial questions! Here are some areas I can assist with:

🏦 **Account Management**
• Current balance and transaction analysis
• Optimal account allocation strategies
• High-yield savings recommendations

📈 **Investment Guidance** 
• Portfolio optimization and rebalancing
• SIP amount calculations and fund selection
• Risk assessment and diversification strategies

💳 **Debt Management**
• Credit card optimization and payoff strategies
• Loan restructuring opportunities
• Debt consolidation analysis

🎯 **Goal Planning**
• Emergency fund calculation and timeline
• Retirement planning and corpus building
• Major purchase planning (house, car, etc.)

📊 **Spending Analysis**
• Expense categorization and budgeting
• Cost-cutting opportunities identification
• Lifestyle optimization recommendations

💰 **Tax Planning**
• 80C optimization strategies
• Tax-efficient investment planning
• Deduction maximization opportunities

🔮 **Predictive Insights**
• Future cashflow analysis
• Goal achievement timelines  
• Risk scenario planning

🤖 **How to interact with me**:
• Ask specific questions: *"How much should I invest monthly?"*
• Request analysis: *"Analyze my spending patterns"*
• Get recommendations: *"Best tax-saving investments for me"*
• Explore scenarios: *"What if I increase my SIP by ₹5000?"*

What would you like to explore today?"""

    await cl.Message(content=content, author="AvestoAI").send()


# Utility functions for chart creation
def create_health_score_gauge(score: int) -> go.Figure:
    """Create health score gauge chart"""

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Financial Health Score", 'font': {'size': 20}},
        delta={'reference': 75, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 40], 'color': '#ffcccc'},
                {'range': [40, 70], 'color': '#ffffcc'},
                {'range': [70, 100], 'color': '#ccffcc'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))

    fig.update_layout(
        paper_bgcolor="white",
        font={'color': "darkblue", 'family': "Arial"},
        height=400
    )

    return fig


def create_net_worth_breakdown(summary: Dict) -> go.Figure:
    """Create net worth breakdown chart"""

    categories = ['Liquid Assets', 'Investments', 'Debt']
    values = [
        summary.get('liquid_assets', 295000),
        summary.get('investments', 630000),
        -summary.get('debt', 35000)
    ]
    colors = ['#2E8B57', '#4169E1', '#DC143C']

    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            text=[f"₹{abs(v / 100000):.1f}L" for v in values],
            textposition='auto',
            textfont=dict(size=12, color='white')
        )
    ])

    fig.update_layout(
        title="Net Worth Breakdown",
        xaxis_title="Categories",
        yaxis_title="Amount (₹)",
        height=400,
        showlegend=False,
        paper_bgcolor='white',
        plot_bgcolor='white'
    )

    return fig


def create_demo_net_worth_chart() -> go.Figure:
    """Create demo net worth chart"""

    categories = ['Liquid Assets', 'Investments', 'Debt']
    values = [295000, 630000, -35000]
    colors = ['#2E8B57', '#4169E1', '#DC143C']

    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            text=[f"₹{abs(v / 100000):.1f}L" for v in values],
            textposition='auto',
            textfont=dict(size=12, color='white')
        )
    ])

    fig.update_layout(
        title="Net Worth Breakdown",
        xaxis_title="Categories",
        yaxis_title="Amount (₹)",
        height=400,
        showlegend=False
    )

    return fig


def create_decision_score_gauge(score: int, amount: int) -> go.Figure:
    """Create decision score gauge"""

    color = "green" if score >= 70 else "orange" if score >= 50 else "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Decision Score<br>₹{amount:,}", 'font': {'size': 18}},
        delta={'reference': 70},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 40], 'color': "lightgray"},
                {'range': [40, 70], 'color': "gray"},
                {'range': [70, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))

    fig.update_layout(height=350)
    return fig


def create_wealth_projection_chart() -> go.Figure:
    """Create wealth projection chart"""

    years = list(range(2025, 2036))
    conservative = [9.1, 10.2, 11.5, 13.1, 14.9, 17.1, 19.6, 22.6, 26.1, 30.2, 35.0]
    moderate = [9.1, 10.8, 12.9, 15.6, 19.1, 23.5, 29.2, 36.4, 45.7, 57.9, 73.5]
    aggressive = [9.1, 11.2, 13.8, 17.2, 21.8, 27.8, 35.9, 46.8, 61.7, 82.1, 109.8]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=years, y=conservative,
        mode='lines+markers',
        name='Conservative (8%)',
        line=dict(color='blue', width=2),
        marker=dict(size=6)
    ))

    fig.add_trace(go.Scatter(
        x=years, y=moderate,
        mode='lines+markers',
        name='Moderate (12%)',
        line=dict(color='green', width=3),
        marker=dict(size=8)
    ))

    fig.add_trace(go.Scatter(
        x=years, y=aggressive,
        mode='lines+markers',
        name='Aggressive (15%)',
        line=dict(color='red', width=2),
        marker=dict(size=6)
    ))

    # Add goal lines
    fig.add_hline(y=20, line_dash="dash", line_color="orange",
                  annotation_text="House Down Payment (₹20L)")
    fig.add_hline(y=50, line_dash="dash", line_color="purple",
                  annotation_text="Financial Independence (₹50L)")

    fig.update_layout(
        title="Wealth Projection Scenarios",
        xaxis_title="Year",
        yaxis_title="Net Worth (₹ Lakhs)",
        height=500,
        hovermode='x unified'
    )

    return fig


def create_goals_progress_chart() -> go.Figure:
    """Create goals progress chart"""

    goals = ['Emergency Fund', 'House Purchase', 'Child Education', 'Retirement']
    current = [78, 42, 8, 3]
    target = [100, 100, 100, 100]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Completed',
        x=goals,
        y=current,
        marker_color=['green' if x >= 75 else 'orange' if x >= 40 else 'red' for x in current],
        text=[f'{x}%' for x in current],
        textposition='auto'
    ))

    fig.add_trace(go.Bar(
        name='Remaining',
        x=goals,
        y=[t - c for t, c in zip(target, current)],
        marker_color='lightgray',
        base=current
    ))

    fig.update_layout(
        title="Financial Goals Progress",
        xaxis_title="Goals",
        yaxis_title="Progress (%)",
        barmode='stack',
        height=400
    )

    return fig


def create_risk_analysis_chart() -> go.Figure:
    """Create risk analysis chart"""

    risk_categories = ['Liquidity', 'Market', 'Inflation', 'Income', 'Debt']
    risk_scores = [20, 60, 55, 15, 10]  # Lower is better
    colors = ['green' if x <= 30 else 'orange' if x <= 60 else 'red' for x in risk_scores]

    fig = go.Figure(data=[
        go.Bar(
            x=risk_categories,
            y=risk_scores,
            marker_color=colors,
            text=[f'{x}%' for x in risk_scores],
            textposition='auto'
        )
    ])

    fig.update_layout(
        title="Risk Assessment by Category",
        xaxis_title="Risk Categories",
        yaxis_title="Risk Level (%)",
        height=400
    )

    return fig


def create_goals_timeline_chart() -> go.Figure:
    """Create goals timeline chart"""

    fig = go.Figure()

    # Goals data
    goals_data = [
        {"goal": "Emergency Fund", "start": "2024-01", "end": "2024-04", "progress": 78},
        {"goal": "House Purchase", "start": "2024-01", "end": "2026-06", "progress": 42},
        {"goal": "Child Education", "start": "2024-01", "end": "2035-12", "progress": 8},
        {"goal": "Retirement", "start": "2024-01", "end": "2055-12", "progress": 3}
    ]

    for i, goal in enumerate(goals_data):
        color = 'green' if goal["progress"] >= 75 else 'orange' if goal["progress"] >= 40 else 'red'

        fig.add_trace(go.Scatter(
            x=[goal["start"], goal["end"]],
            y=[i, i],
            mode='lines+markers',
            name=goal["goal"],
            line=dict(color=color, width=8),
            marker=dict(size=10)
        ))

    fig.update_layout(
        title="Goals Timeline & Progress",
        xaxis_title="Timeline",
        yaxis_title="Goals",
        height=400,
        yaxis=dict(tickmode='array', tickvals=list(range(len(goals_data))),
                   ticktext=[g["goal"] for g in goals_data])
    )

    return fig


def create_chart_from_data(chart_data: Dict) -> go.Figure:
    """Create Plotly chart from AI response data"""

    chart_type = chart_data.get("type", "bar")
    title = chart_data.get("title", "Chart")
    data = chart_data.get("data", {})

    labels = data.get("labels", [])
    values = data.get("values", [])

    if chart_type == "pie":
        fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
    elif chart_type == "line":
        fig = go.Figure(data=[go.Scatter(x=labels, y=values, mode='lines+markers')])
    else:  # bar chart
        fig = go.Figure(data=[go.Bar(x=labels, y=values)])

    fig.update_layout(title=title, height=400)
    return fig


def determine_category(description: str) -> str:
    """Determine category from purchase description"""

    description_lower = description.lower()

    if any(word in description_lower for word in ['laptop', 'computer', 'phone', 'iphone', 'macbook', 'ipad']):
        return 'electronics'
    elif any(word in description_lower for word in ['car', 'bike', 'vehicle', 'automobile']):
        return 'transportation'
    elif any(word in description_lower for word in ['house', 'home', 'property', 'apartment']):
        return 'real_estate'
    elif any(word in description_lower for word in ['course', 'education', 'training', 'certification']):
        return 'education'
    elif any(word in description_lower for word in ['vacation', 'travel', 'trip', 'holiday']):
        return 'travel'
    elif any(word in description_lower for word in ['investment', 'stocks', 'mutual fund', 'sip']):
        return 'investment'
    elif any(word in description_lower for word in ['medical', 'health', 'treatment', 'surgery']):
        return 'health'
    else:
        return 'general'


if __name__ == "__main__":
    cl.run()
