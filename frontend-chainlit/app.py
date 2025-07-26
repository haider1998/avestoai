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

# Global variables for Fi MCP authentication
user_mobile = None
session_id = None
current_scenario = "balanced"
is_authenticated = False


@cl.on_chat_start
async def start():
    """Initialize chat session with Fi MCP authentication"""
    global user_mobile, session_id, current_scenario, is_authenticated

    # Welcome message with mobile number collection
    await cl.Message(
        content="🔮 **Welcome to AvestoAI with Fi Money Integration!**\n\n"
                "I'm connected to Fi Money's real financial data using their MCP server.\n\n"
                "**To get started, I need your mobile number for Fi Money authentication.**\n\n"
                "📱 Please enter your 10-digit mobile number:",
        author="AvestoAI"
    ).send()


@cl.on_message
async def main(message: cl.Message):
    """Handle user messages with Fi MCP authentication flow"""
    global user_mobile, session_id, current_scenario, is_authenticated

    user_input = message.content.strip()

    # Handle mobile number input
    if not user_mobile and user_input.isdigit() and len(user_input) == 10:
        await handle_mobile_number_input(user_input)
        return

    # Handle OTP input
    if user_mobile and not is_authenticated and user_input.isdigit():
        await handle_otp_input(user_input)
        return

    # Handle scenario selection
    if user_input.lower() in ["1", "2", "3", "4", "5", "6"] or any(
            word in user_input.lower() for word in ["scenario", "switch", "change data"]):
        await handle_scenario_selection(user_input)
        return

    # Check authentication before processing queries
    if not is_authenticated:
        await cl.Message(
            content="🔐 **Authentication Required**\n\n"
                    "Please complete Fi Money authentication first by providing:\n"
                    "1. Your 10-digit mobile number\n"
                    "2. OTP (any 6-digit number works in demo)\n\n"
                    "📱 Enter your mobile number:",
            author="AvestoAI"
        ).send()
        return

    # Process authenticated queries
    if any(word in user_input.lower() for word in
           ["opportunity", "opportunities", "optimize", "save money", "improve"]):
        await handle_opportunity_request(user_input)
    elif any(word in user_input.lower() for word in ["should i buy", "purchase", "decision", "score", "worth buying"]):
        await handle_decision_scoring(user_input)
    elif any(word in user_input.lower() for word in ["health", "score", "status", "dashboard", "overview"]):
        await show_financial_dashboard()
    elif any(word in user_input.lower() for word in ["predict", "future", "forecast", "timeline", "projection"]):
        await handle_prediction_request(user_input)
    elif any(word in user_input.lower() for word in ["alert", "warning", "risk", "problem"]):
        await handle_risk_analysis()
    else:
        await handle_general_query(user_input)


async def handle_mobile_number_input(mobile_number: str):
    """Handle mobile number input and initiate Fi MCP authentication"""
    global user_mobile, session_id, current_scenario

    try:
        user_mobile = mobile_number

        await cl.Message(
            content=f"📱 **Mobile Number Received: {mobile_number}**\n\n"
                    f"🎭 **Choose your financial scenario:**\n"
                    f"1. 📊 **Balanced Portfolio** - Well-diversified investor\n"
                    f"2. 🚀 **High Growth** - Large portfolio with multiple assets\n"
                    f"3. 💰 **SIP Investor** - Consistent monthly investments\n"
                    f"4. 🏦 **Conservative** - Fixed income focused\n"
                    f"5. 😰 **Debt Heavy** - High liabilities, needs help\n"
                    f"6. 🌱 **Starter** - Just beginning investment journey\n\n"
                    f"Type the number (1-6) to select scenario:",
            author="AvestoAI"
        ).send()

    except Exception as e:
        await cl.Message(
            content=f"❌ **Error processing mobile number**: {str(e)}\n\n"
                    f"Please try again with a valid 10-digit mobile number.",
            author="AvestoAI"
        ).send()


async def handle_scenario_selection(scenario_input: str):
    """Handle scenario selection and initiate Fi MCP session"""
    global user_mobile, session_id, current_scenario

    scenario_map = {
        "1": "balanced",
        "2": "all_assets_large",
        "3": "sip_investor",
        "4": "fixed_income",
        "5": "debt_heavy",
        "6": "starter"
    }

    scenario = scenario_map.get(scenario_input.strip(), "balanced")
    current_scenario = scenario

    try:
        await cl.Message(
            content=f"🎭 **Scenario Selected**: {scenario.replace('_', ' ').title()}\n\n"
                    f"🔐 **Initiating Fi Money authentication...**",
            author="AvestoAI"
        ).send()

        # Initiate Fi MCP authentication
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/fi-auth/initiate",
                json={
                    "mobile_number": user_mobile,
                    "scenario": scenario
                }
            )

            if response.status_code == 200:
                auth_data = response.json()
                session_id = auth_data["session_id"]

                if auth_data.get("requires_authentication") and auth_data.get("login_url"):
                    await cl.Message(
                        content=f"🔐 **Authentication Required**\n\n"
                                f"Session ID: `{session_id}`\n"
                                f"Login URL: {auth_data['login_url']}\n\n"
                                f"**For demo purposes, enter any 6-digit number as OTP:**",
                        author="AvestoAI"
                    ).send()
                else:
                    # Already authenticated
                    global is_authenticated
                    is_authenticated = True
                    await cl.Message(
                        content="✅ **Authentication successful!**\n\n"
                                "Let me fetch your financial data...",
                        author="AvestoAI"
                    ).send()
                    await show_financial_dashboard()
            else:
                raise Exception(f"HTTP {response.status_code}")

    except Exception as e:
        await cl.Message(
            content=f"❌ **Authentication initiation failed**: {str(e)}\n\n"
                    f"Please try again or contact support.",
            author="AvestoAI"
        ).send()


async def handle_otp_input(otp: str):
    """Handle OTP input for Fi MCP authentication"""
    global user_mobile, session_id, is_authenticated

    try:
        await cl.Message(
            content=f"🔐 **Verifying OTP**: {otp}\n\n"
                    f"Please wait...",
            author="AvestoAI"
        ).send()

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/fi-auth/verify",
                json={
                    "session_id": session_id,
                    "mobile_number": user_mobile,
                    "otp": otp
                }
            )

            if response.status_code == 200:
                auth_result = response.json()

                if auth_result.get("success"):
                    is_authenticated = True

                    await cl.Message(
                        content=f"✅ **Authentication Successful!**\n\n"
                                f"📱 Mobile: {user_mobile}\n"
                                f"🎭 Scenario: {auth_result.get('scenario', 'Unknown')}\n"
                                f"💰 Net Worth: ₹{auth_result.get('net_worth', 0):,.0f}\n"
                                f"🏦 Accounts: {auth_result.get('accounts_count', 0)}\n\n"
                                f"🔍 **Now analyzing your financial data...**",
                        author="AvestoAI"
                    ).send()

                    # Show dashboard
                    await show_financial_dashboard()
                else:
                    await cl.Message(
                        content=f"❌ **Authentication Failed**: {auth_result.get('message', 'Unknown error')}\n\n"
                                f"Please try again with a different OTP:",
                        author="AvestoAI"
                    ).send()
            else:
                raise Exception(f"HTTP {response.status_code}")

    except Exception as e:
        await cl.Message(
            content=f"❌ **OTP verification failed**: {str(e)}\n\n"
                    f"Please try again:",
            author="AvestoAI"
        ).send()


async def show_financial_dashboard():
    """Display comprehensive financial dashboard using Fi MCP data"""
    global user_mobile

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(
                f"{API_BASE_URL}/api/v1/financial-dashboard/{user_mobile}"
            )

            if response.status_code == 200:
                dashboard_data = response.json()
                await display_dashboard_data(dashboard_data)
            else:
                await display_demo_dashboard()

    except Exception as e:
        await cl.Message(
            content=f"⚠️ **Dashboard Error**: {str(e)}\n\n"
                    f"Showing demo data instead...",
            author="AvestoAI"
        ).send()
        await display_demo_dashboard()


async def display_dashboard_data(dashboard_data: Dict):
    """Display dashboard with real Fi MCP data"""

    summary = dashboard_data.get("financial_summary", {})
    health_score = dashboard_data.get("health_score", 75)
    insights = dashboard_data.get("insights", [])
    scenario = dashboard_data.get("scenario", "balanced")

    # Create health score gauge
    health_chart = create_health_score_gauge(health_score)

    # Create net worth chart
    net_worth_chart = create_net_worth_breakdown(summary)

    # Format dashboard message
    content = f"📊 **Your Fi Money Financial Dashboard**\n\n"
    content += f"🎭 **Scenario**: {scenario.replace('_', ' ').title()}\n"
    content += f"📱 **Mobile**: {user_mobile}\n\n"
    content += f"💰 **Net Worth**: ₹{summary.get('net_worth', 0):,.0f}\n"
    content += f"💵 **Liquid Assets**: ₹{summary.get('liquid_assets', 0):,.0f}\n"
    content += f"📈 **Investments**: ₹{summary.get('investments', 0):,.0f}\n"
    content += f"💳 **Debt**: ₹{summary.get('debt', 0):,.0f}\n"
    content += f"💸 **Monthly Cash Flow**: ₹{summary.get('monthly_income', 0) - summary.get('monthly_expenses', 0):,.0f}\n"
    content += f"🛡️ **Emergency Fund**: {summary.get('emergency_fund_months', 0):.1f} months\n\n"

    content += f"🏥 **Financial Health Score**: {health_score}/100\n\n"

    if insights:
        content += "💡 **Fi Money Insights**:\n"
        for insight in insights[:3]:
            content += f"• {insight}\n"
        content += "\n"

    content += "🔍 **Ask me anything about your finances:**\n"
    content += "• *\"What opportunities do you see?\"*\n"
    content += "• *\"Should I buy a laptop for ₹80,000?\"*\n"
    content += "• *\"Switch to debt heavy scenario\"*\n"
    content += "• *\"What's my investment performance?\"*"

    elements = [
        cl.Plotly(name="health_score", figure=health_chart, display="inline"),
        cl.Plotly(name="net_worth", figure=net_worth_chart, display="inline")
    ]

    await cl.Message(
        content=content,
        elements=elements
    ).send()


async def handle_opportunity_request(user_message: str):
    """Handle requests for financial opportunities using Fi MCP data"""
    global user_mobile

    await cl.Message(
        content="🔍 **Analyzing your Fi Money data for opportunities...**\n\n"
                "Using real financial data from Fi MCP server...",
        author="AvestoAI"
    ).send()

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/analyze-opportunities",
                json={
                    "mobile_number": user_mobile,
                    "analysis_type": "comprehensive",
                    "include_predictions": True,
                    "time_horizon": "1_year"
                }
            )

            if response.status_code == 200:
                opportunities_data = response.json()
                await display_opportunities(opportunities_data)
            elif response.status_code == 401:
                await cl.Message(
                    content="🔐 **Authentication expired**. Please restart the session.",
                    author="AvestoAI"
                ).send()
            else:
                await display_demo_opportunities()

    except Exception as e:
        await cl.Message(
            content=f"⚠️ **Error**: {str(e)}\n\nShowing demo opportunities...",
            author="AvestoAI"
        ).send()
        await display_demo_opportunities()


async def handle_decision_scoring(user_message: str):
    """Handle financial decision scoring using Fi MCP data"""
    global user_mobile

    # Try to extract amount and item from message
    import re
    amount_match = re.search(r'₹?(\d+(?:,\d+)*(?:\.\d+)?)', user_message)

    if amount_match:
        amount = int(amount_match.group(1).replace(',', ''))
        await score_financial_decision(user_message, amount)
    else:
        await cl.Message(
            content="🎯 **Decision Scorer with Fi Money Data**\n\n"
                    "I'll analyze any purchase using your real financial data from Fi Money!\n\n"
                    "Please tell me:\n"
                    "1. What are you considering buying?\n"
                    "2. How much does it cost?\n\n"
                    "Example: *\"Should I buy a MacBook Pro for ₹150,000?\"*",
            author="AvestoAI"
        ).send()


async def score_financial_decision(description: str, amount: int):
    """Score a specific financial decision using Fi MCP data"""
    global user_mobile

    await cl.Message(
        content=f"🎯 **Analyzing your decision with Fi Money data...**\n\n"
                f"**Purchase**: {description}\n"
                f"**Amount**: ₹{amount:,}\n\n"
                f"Evaluating against your real financial situation...",
        author="AvestoAI"
    ).send()

    try:
        # Determine category from description
        category = determine_category(description)

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/predict-decision",
                json={
                    "mobile_number": user_mobile,
                    "amount": amount,
                    "category": category,
                    "description": description,
                    "financing_method": "cash",
                    "user_context": {}
                }
            )

            if response.status_code == 200:
                decision_data = response.json()
                await display_decision_analysis(decision_data, amount, description)
            elif response.status_code == 401:
                await cl.Message(
                    content="🔐 **Authentication expired**. Please restart the session.",
                    author="AvestoAI"
                ).send()
            else:
                await display_demo_decision_analysis(amount, category, description)

    except Exception as e:
        await cl.Message(
            content=f"⚠️ **Error**: {str(e)}\n\nShowing demo analysis...",
            author="AvestoAI"
        ).send()
        await display_demo_decision_analysis(amount, "electronics", description)


async def handle_general_query(user_message: str):
    """Handle general financial queries using Fi MCP data"""
    global user_mobile

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/chat",
                json={
                    "mobile_number": user_mobile,
                    "message": user_message,
                    "include_charts": True,
                    "context_type": "general"
                }
            )

            if response.status_code == 200:
                chat_data = response.json()
                await display_chat_response(chat_data)
            elif response.status_code == 401:
                await cl.Message(
                    content="🔐 **Authentication expired**. Please restart the session.",
                    author="AvestoAI"
                ).send()
            else:
                await display_fallback_response(user_message)

    except Exception as e:
        await cl.Message(
            content=f"⚠️ **Error**: {str(e)}\n\nUsing fallback response...",
            author="AvestoAI"
        ).send()
        await display_fallback_response(user_message)


# Keep all the display and utility functions from previous implementation
# (create_health_score_gauge, display_opportunities, etc.)

async def display_opportunities(opportunities_data: Dict):
    """Display opportunities from Fi MCP analysis"""

    opportunities = opportunities_data.get("opportunities", [])
    total_value = opportunities_data.get("total_annual_value", 0)
    mobile_number = opportunities_data.get("mobile_number", "")

    if not opportunities:
        await cl.Message(
            content="🎉 **Great news!** Your Fi Money data shows well-optimized finances!\n\n"
                    "Keep up the excellent financial discipline!",
            author="AvestoAI"
        ).send()
        return

    content = f"💡 **Financial Opportunities from Fi Money Data**\n\n"
    content += f"📱 **Mobile**: {mobile_number}\n"
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
    content += "• *\"What are the risks of these opportunities?\"*\n"
    content += "• *\"Switch to a different scenario\"*"

    await cl.Message(content=content, author="AvestoAI").send()


# Include all other utility functions (create charts, etc.)
def create_health_score_gauge(score: int) -> go.Figure:
    """Create health score gauge chart"""

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Fi Money Financial Health Score", 'font': {'size': 20}},
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
        title="Fi Money Net Worth Breakdown",
        xaxis_title="Categories",
        yaxis_title="Amount (₹)",
        height=400,
        showlegend=False,
        paper_bgcolor='white',
        plot_bgcolor='white'
    )

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


# Include other required functions for demo fallbacks
async def display_demo_dashboard():
    """Display demo dashboard when Fi MCP is unavailable"""

    health_chart = create_health_score_gauge(78)
    net_worth_chart = create_demo_net_worth_chart()

    content = f"""📊 **Fi Money Dashboard (Demo Mode)**

📱 **Mobile**: {user_mobile}
🎭 **Scenario**: {current_scenario}

💰 **Net Worth**: ₹9.1 Lakhs
💵 **Liquid Assets**: ₹2.95 Lakhs  
📈 **Investments**: ₹6.3 Lakhs
💳 **Debt**: ₹35,000
💸 **Monthly Cash Flow**: ₹45,000
🛡️ **Emergency Fund**: 3.9 months

🏥 **Financial Health Score**: 78/100

💡 **Fi Money Insights**:
• Your net worth increased by ₹45,000 this month - excellent progress!
• Consider moving ₹50,000 to high-yield investments for better returns
• Emergency fund is strong, but could be optimized for higher yield

🔍 **Try asking**:
• *"What opportunities do you see in my finances?"*
• *"Should I buy a MacBook for ₹150,000?"*
• *"Switch to debt heavy scenario"*"""

    elements = [
        cl.Plotly(name="health_score", figure=health_chart, display="inline"),
        cl.Plotly(name="net_worth", figure=net_worth_chart, display="inline")
    ]

    await cl.Message(
        content=content,
        elements=elements
    ).send()


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
        title="Fi Money Net Worth Breakdown (Demo)",
        xaxis_title="Categories",
        yaxis_title="Amount (₹)",
        height=400,
        showlegend=False
    )

    return fig


# Include other required demo functions...
async def display_demo_opportunities():
    """Display demo opportunities"""

    content = f"""💡 **Financial Opportunities (Demo Data)**

📱 **Mobile**: {user_mobile}
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
• *"Switch to a different scenario to see how opportunities change"*"""

    await cl.Message(content=content, author="AvestoAI").send()


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
        analysis = f"Based on your Fi Money data, this {category} purchase aligns well with your financial goals."
    elif score >= 50:
        score_emoji = "🟡"
        score_text = "Consider Carefully"
        analysis = f"This {category} purchase is feasible but consider the opportunity cost based on your Fi Money portfolio."
    else:
        score_emoji = "🔴"
        score_text = "Reconsider"
        analysis = f"Based on your Fi Money financial situation, this {category} purchase may strain your finances."

    content = f"""🎯 **Fi Money Decision Analysis**

📱 **Mobile**: {user_mobile}
**Purchase**: {description}
**Amount**: ₹{amount:,}

{score_emoji} **Score**: {score}/100 - {score_text}

**Analysis**: {analysis}

📈 **Impact on Fi Money Portfolio**:
• 5-year opportunity cost if invested: ₹{amount * 1.6:,.0f}
• Impact on emergency fund: Minimal
• Effect on financial goals: {['Delayed', 'Minimal', 'Positive'][score // 35]}

💡 **Recommendation**: {"Proceed with purchase" if score >= 70 else "Consider waiting 2-3 months" if score >= 50 else "Explore alternatives or wait 6 months"}

💬 **Want to explore more?**
• *"What if I finance this instead of paying cash?"*
• *"Show me the impact on my retirement planning"*
• *"Switch to starter scenario to see how this decision looks for a beginner"*"""

    await cl.Message(
        content=content,
        elements=[cl.Plotly(name="decision_score", figure=create_decision_score_gauge(score, amount), display="inline")]
    ).send()


def create_decision_score_gauge(score: int, amount: int) -> go.Figure:
    """Create decision score gauge"""

    color = "green" if score >= 70 else "orange" if score >= 50 else "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Fi Money Decision Score<br>₹{amount:,}", 'font': {'size': 18}},
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


# Include other required functions...
async def display_chat_response(chat_data: Dict):
    """Display AI chat response"""

    response_text = chat_data.get("response", "")
    suggestions = chat_data.get("suggestions", [])
    charts = chat_data.get("charts", [])
    mobile_number = chat_data.get("mobile_number", "")

    content = f"💡 **AI Financial Advisor (Fi Money Data)**\n\n"
    content += f"📱 **Mobile**: {mobile_number}\n\n"
    content += response_text

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

    content = f"""💡 **AI Financial Advisor (Fi Money Integration)**

📱 **Mobile**: {user_mobile}

I'm here to help with all your financial questions using real Fi Money data!

🏦 **Account Management**
• Current balance and transaction analysis from Fi Money
• Optimal account allocation strategies
• High-yield savings recommendations

📈 **Investment Guidance** 
• Portfolio optimization using your Fi Money investments
• SIP amount calculations and fund selection
• Risk assessment and diversification strategies

💳 **Debt Management**
• Credit card optimization from Fi Money credit data
• Loan restructuring opportunities
• Debt consolidation analysis

🎯 **Goal Planning**
• Emergency fund calculation and timeline
• Retirement planning and corpus building
• Major purchase planning (house, car, etc.)

🎭 **Scenario Testing**
• Switch between different financial scenarios
• See how your decisions look in different situations
• Compare "balanced" vs "debt heavy" vs "high growth" profiles

🤖 **How to interact with me**:
• Ask specific questions: *"How much should I invest monthly?"*
• Request analysis: *"Analyze my Fi Money spending patterns"*
• Test scenarios: *"Switch to starter scenario"*
• Get recommendations: *"Best tax-saving investments for me"*

What would you like to explore with your Fi Money data today?"""

    await cl.Message(content=content, author="AvestoAI").send()


def create_chart_from_data(chart_data: Dict) -> go.Figure:
    """Create Plotly chart from AI response data"""

    chart_type = chart_data.get("type", "bar")
    title = chart_data.get("title", "Fi Money Chart")
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


if __name__ == "__main__":
    cl.run()
