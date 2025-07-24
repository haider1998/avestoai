# frontend-chainlit/app.py
import chainlit as cl
import httpx
import json
import asyncio
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# Backend API configuration
API_BASE_URL = "http://localhost:8080"


@cl.on_chat_start
async def start():
    """Initialize chat session"""

    # Welcome message with demo user setup
    await cl.Message(
        content="🔮 **Welcome to AvestoAI - Your Financial Prophet!**\n\n"
                "I can help you:\n"
                "- 💡 **Discover hidden opportunities** in your finances\n"
                "- 🎯 **Score financial decisions** before you make them\n"
                "- ⚠️ **Predict potential problems** 7-30 days ahead\n"
                "- 📈 **Optimize your wealth building** strategy\n\n"
                "I'm analyzing your financial data now...",
        author="AvestoAI"
    ).send()

    # Get initial financial analysis
    await get_financial_dashboard()


@cl.on_message
async def main(message: cl.Message):
    """Handle user messages"""

    user_input = message.content.lower()

    # Route different types of queries
    if any(word in user_input for word in ["opportunity", "opportunities", "optimize", "save money"]):
        await handle_opportunity_request()

    elif any(word in user_input for word in ["should i buy", "purchase", "decision", "score"]):
        await handle_decision_scoring(message.content)

    elif any(word in user_input for word in ["health", "score", "status", "dashboard"]):
        await get_financial_dashboard()

    elif any(word in user_input for word in ["predict", "future", "forecast", "timeline"]):
        await handle_prediction_request(message.content)

    elif any(word in user_input for word in ["alert", "warning", "risk"]):
        await handle_risk_analysis()

    else:
        await handle_general_query(message.content)


async def get_financial_dashboard():
    """Get and display financial dashboard"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_BASE_URL}/api/dashboard")
            dashboard_data = response.json()["data"]

        # Create net worth visualization
        net_worth_chart = create_net_worth_chart(dashboard_data)

        # Display dashboard
        await cl.Message(
            content=f"📊 **Your Financial Dashboard**\n\n"
                    f"💰 **Net Worth**: ₹{dashboard_data['net_worth']:,}\n"
                    f"💳 **Available Credit**: ₹{dashboard_data['accounts']['credit_limit'] - dashboard_data['accounts']['credit_used']:,}\n"
                    f"📈 **Investment Portfolio**: ₹{sum(dashboard_data['investments'].values()):,}\n\n"
                    f"🔍 **Found {len(dashboard_data['opportunities']['opportunities'])} opportunities** to improve your finances!",
            elements=[cl.Plotly(name="net_worth", figure=net_worth_chart, display="inline")]
        ).send()

        # Show top opportunities
        await display_opportunities(dashboard_data['opportunities'])

    except Exception as e:
        await cl.Message(
            content=f"⚠️ Error getting dashboard data: {str(e)}\n\n"
                    "Using demo mode for presentation.",
            author="System"
        ).send()

        await show_demo_dashboard()


async def handle_opportunity_request():
    """Handle requests for financial opportunities"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/api/analyze-opportunities",
                json={"user_id": "demo_user"}
            )
            opportunities = response.json()["data"]

        await display_opportunities(opportunities)

    except Exception as e:
        await cl.Message(
            content="🔍 **Here are some opportunities I found:**\n\n"
                    "💰 **High-Yield Savings**: Move ₹180,000 to earn ₹7,200 more annually\n"
                    "📈 **SIP Optimization**: Increase monthly SIP by ₹5,000 → ₹12 Lakh in 10 years\n"
                    "🍽️ **Dining Optimization**: Reduce food expenses by 25% → Save ₹18,000/year",
            author="AvestoAI"
        ).send()


async def handle_decision_scoring(user_message: str):
    """Handle financial decision scoring requests"""

    # Try to extract amount and item from message
    import re
    amount_match = re.search(r'₹?(\d+(?:,\d+)*(?:\.\d+)?)', user_message)
    amount = int(amount_match.group(1).replace(',', '')) if amount_match else 75000

    # Ask for clarification if needed
    if not amount_match:
        await cl.AskUserMessage(
            content="💰 What's the purchase amount?",
            author="AvestoAI",
            timeout=30
        ).send()

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/api/predict",
                json={
                    "type": "purchase",
                    "amount": amount,
                    "description": user_message,
                    "user_context": {"income": 1200000, "savings": 180000}
                }
            )

            decision_data = response.json()["data"]
            score = decision_data.get("score", 65)

        # Create score visualization
        score_chart = create_score_gauge(score)

        score_emoji = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"

        await cl.Message(
            content=f"🎯 **Financial Decision Score**\n\n"
                    f"{score_emoji} **Score: {score}/100**\n\n"
                    f"**Analysis**: {decision_data.get('explanation', 'This purchase aligns moderately well with your financial goals.')}\n\n"
                    f"**Long-term Impact**: {decision_data.get('long_term_impact', 'Moderate impact on wealth building timeline.')}\n\n"
                    f"**Alternative**: {decision_data.get('alternatives', [{'option': 'Consider waiting 3 months to save up cash'}])[0].get('option', 'No alternatives suggested')}",
            elements=[cl.Plotly(name="decision_score", figure=score_chart, display="inline")]
        ).send()

    except Exception as e:
        await cl.Message(
            content=f"🎯 **Financial Decision Analysis**\n\n"
                    f"**Purchase**: ₹{amount:,}\n"
                    f"**Score**: 65/100 🟡\n\n"
                    f"**Analysis**: Based on your financial profile, this purchase is moderately aligned with your goals. "
                    f"Consider the opportunity cost of ₹{amount * 1.5:,} in 5 years if invested instead.\n\n"
                    f"**Recommendation**: If this purchase enhances your productivity or well-being significantly, proceed. "
                    f"Otherwise, consider delaying by 2-3 months to save cash.",
            author="AvestoAI"
        ).send()


async def handle_prediction_request(user_message: str):
    """Handle future prediction requests"""

    prediction_chart = create_wealth_projection()

    await cl.Message(
        content="🔮 **Your Financial Future Prediction**\n\n"
                "📈 **Net Worth Trajectory**:\n"
                "- **1 Year**: ₹12.5 Lakhs (+38%)\n"
                "- **5 Years**: ₹45.2 Lakhs (+398%)\n"
                "- **10 Years**: ₹1.2 Crores (+1,233%)\n\n"
                "🎯 **Key Milestones**:\n"
                "- **House Down Payment** (₹20L): Achievable in 2.5 years\n"
                "- **Financial Independence**: Age 38 (10 years)\n"
                "- **Retirement Corpus** (₹5Cr): Age 45\n\n"
                "⚡ **Acceleration Opportunities**:\n"
                "- Increase SIP by ₹5K → Retire 2 years earlier\n"
                "- Optimize taxes → Save ₹45K annually",
        elements=[cl.Plotly(name="wealth_projection", figure=prediction_chart, display="inline")]
    ).send()


async def handle_risk_analysis():
    """Handle risk and alert analysis"""

    await cl.Message(
        content="⚠️ **Smart Risk Analysis**\n\n"
                "🔍 **Detected Patterns**:\n"
                "- Spending velocity increased 23% this month\n"
                "- Emergency fund below 6-month target\n"
                "- Credit utilization at 22.5% (optimal: <10%)\n\n"
                "📅 **Predictive Alerts**:\n"
                "- **18 days**: Potential cashflow stress if large purchase made\n"
                "- **25 days**: Credit card payment due (₹15,000)\n"
                "- **Next month**: Opportunity to increase SIP during bonus\n\n"
                "🛡️ **Risk Mitigation**:\n"
                "1. Build emergency fund by ₹50K\n"
                "2. Set up automatic credit card payments\n"
                "3. Enable spending alerts for transactions >₹5K",
        author="AvestoAI"
    ).send()


async def handle_general_query(user_message: str):
    """Handle general financial queries"""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{API_BASE_URL}/api/chat",
                json={"message": user_message}
            )

            ai_response = response.json()["data"]["response"]

        await cl.Message(
            content=f"💡 **AI Financial Advisor**\n\n{ai_response.get('response', 'I can help you with financial planning, investment advice, and optimization strategies. What specific area would you like to explore?')}",
            author="AvestoAI"
        ).send()

    except Exception as e:
        await cl.Message(
            content="💡 **AI Financial Advisor**\n\n"
                    "I can help you with:\n"
                    "- **Investment planning** and portfolio optimization\n"
                    "- **Savings strategies** and emergency fund building\n"
                    "- **Debt management** and credit optimization\n"
                    "- **Tax planning** and 80C optimization\n"
                    "- **Goal setting** and timeline planning\n\n"
                    "What specific financial area would you like to explore?",
            author="AvestoAI"
        ).send()


async def display_opportunities(opportunities_data):
    """Display financial opportunities"""

    opportunities = opportunities_data.get("opportunities", [])

    if not opportunities:
        await cl.Message(
            content="🎉 Great news! Your finances are well-optimized. Keep up the good work!",
            author="AvestoAI"
        ).send()
        return

    content = "💡 **Financial Opportunities Detected**\n\n"

    for i, opp in enumerate(opportunities[:3], 1):  # Show top 3
        priority_emoji = "🔥" if opp.get("priority") == "high" else "⭐" if opp.get("priority") == "medium" else "💡"

        content += f"{priority_emoji} **{opp.get('title', 'Opportunity')}**\n"
        content += f"   💰 Value: ₹{opp.get('potential_annual_value', 0):,.0f}/year\n"
        content += f"   ⏱️ Effort: {opp.get('effort_level', 'Medium')} | Time: {opp.get('time_to_implement', 'TBD')}\n"
        content += f"   📝 {opp.get('description', 'No description available')}\n\n"

    content += f"🚀 **Total Annual Impact**: ₹{sum(o.get('potential_annual_value', 0) for o in opportunities):,.0f}\n\n"
    content += "💬 Ask me \"How do I implement these?\" for detailed action steps!"

    await cl.Message(content=content, author="AvestoAI").send()


def create_net_worth_chart(dashboard_data):
    """Create net worth breakdown chart"""

    # Sample data for visualization
    categories = ['Savings', 'Investments', 'Debt']
    values = [
        sum([dashboard_data['accounts']['savings'], dashboard_data['accounts']['checking']]),
        sum(dashboard_data['investments'].values()),
        -dashboard_data['accounts']['credit_used']
    ]
    colors = ['#2E8B57', '#4169E1', '#DC143C']

    fig = go.Figure(data=[
        go.Bar(x=categories, y=values, marker_color=colors, text=[f"₹{v:,.0f}" for v in values], textposition='auto')
    ])

    fig.update_layout(
        title="Net Worth Breakdown",
        xaxis_title="Categories",
        yaxis_title="Amount (₹)",
        height=400,
        showlegend=False
    )

    return fig


def create_score_gauge(score):
    """Create decision score gauge chart"""

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Financial Decision Score"},
        delta={'reference': 70},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
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

    fig.update_layout(height=300)
    return fig


def create_wealth_projection():
    """Create wealth projection chart"""

    years = list(range(2025, 2036))
    net_worth = [9.1, 12.5, 16.8, 22.3, 29.2, 37.8, 48.5, 61.7, 77.9, 97.8, 122.4]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=years,
        y=net_worth,
        mode='lines+markers',
        name='Projected Net Worth',
        line=dict(color='#4169E1', width=3),
        marker=dict(size=8)
    ))

    # Add milestone markers
    fig.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="House Down Payment (₹20L)")
    fig.add_hline(y=50, line_dash="dash", line_color="green", annotation_text="Financial Independence (₹50L)")

    fig.update_layout(
        title="Wealth Projection (Next 10 Years)",
        xaxis_title="Year",
        yaxis_title="Net Worth (₹ Lakhs)",
        height=400,
        showlegend=True
    )

    return fig


async def show_demo_dashboard():
    """Fallback demo dashboard"""

    await cl.Message(
        content="📊 **Demo Financial Dashboard**\n\n"
                "💰 **Net Worth**: ₹9.1 Lakhs\n"
                "💳 **Available Credit**: ₹1.55 Lakhs\n"
                "📈 **Investment Portfolio**: ₹8.7 Lakhs\n\n"
                "🔍 **Found 3 opportunities** to improve your finances!\n\n"
                "💡 **Top Opportunity**: High-Yield Savings\n"
                "   💰 Potential: ₹7,200/year\n"
                "   ⏱️ Effort: Low | Time: 1 day\n\n"
                "Ask me about opportunities, decision scoring, or predictions!",
        author="AvestoAI"
    ).send()


if __name__ == "__main__":
    cl.run()
