# tools/finance_advisor.py
from google.adk.tools.tool_context import ToolContext
from typing import Dict, Any, List, Optional

def get_financial_advice(
    topic: str,
    risk_profile: Optional[str] = "moderate",
    tool_context: ToolContext = None
) -> Dict[str, Any]:
    """Provides financial advice on various topics.
    
    This tool offers general financial guidance based on the specified topic and risk profile.
    
    Args:
        topic (str): The financial topic to get advice on (e.g., "savings", "investment", "retirement")
        risk_profile (str, optional): The user's risk tolerance level ("conservative", "moderate", "aggressive").
                                      Defaults to "moderate".
        tool_context (ToolContext, optional): Provides access to session state and context information
    
    Returns:
        Dict[str, Any]: A dictionary containing the advice with keys:
            - status: 'success' or 'error'
            - advice: List of advice points (if successful)
            - resources: List of additional resources (if successful)
            - error_message: Description of the error (if status is 'error')
    """
    print(f"--- Tool: get_financial_advice called for topic: {topic}, risk profile: {risk_profile} ---")
    
    # Normalize inputs
    topic_normalized = topic.lower().strip()
    risk_profile_normalized = risk_profile.lower().strip()
    
    # Validate risk profile
    valid_risk_profiles = ["conservative", "moderate", "aggressive"]
    if risk_profile_normalized not in valid_risk_profiles:
        return {
            "status": "error",
            "error_message": f"Invalid risk profile: '{risk_profile}'. Please use one of: {', '.join(valid_risk_profiles)}"
        }
    
    # Mock financial advice database
    advice_db = {
        "savings": {
            "conservative": {
                "advice": [
                    "Build an emergency fund covering 6-9 months of expenses",
                    "Consider high-yield savings accounts or CDs for better returns",
                    "Set up automatic transfers to your savings account",
                    "Minimize fees by using no-fee banking services"
                ],
                "resources": [
                    "FDIC: Savings Accounts Guide",
                    "Consumer Financial Protection Bureau: Building a Savings Cushion"
                ]
            },
            "moderate": {
                "advice": [
                    "Maintain an emergency fund of 3-6 months of expenses",
                    "Consider a mix of high-yield savings and short-term bond funds",
                    "Use tax-advantaged savings accounts when possible",
                    "Automate regular contributions to your savings"
                ],
                "resources": [
                    "Federal Reserve: Personal Finance Education Resources",
                    "MyMoney.gov: Saving and Investing"
                ]
            },
            "aggressive": {
                "advice": [
                    "Keep a minimal emergency fund (3 months) and invest the rest",
                    "Consider money market accounts for slightly higher yields",
                    "Use savings as a short-term holding area before investing",
                    "Optimize your cash flow to maximize investment contributions"
                ],
                "resources": [
                    "Investor.gov: Saving and Investing",
                    "SEC: Beginners' Guide to Asset Allocation"
                ]
            }
        },
        "investment": {
            "conservative": {
                "advice": [
                    "Focus on preservation of capital with government and high-quality corporate bonds",
                    "Consider dividend-paying blue-chip stocks (20-30% of portfolio)",
                    "Use broad market index funds for diversification",
                    "Limit exposure to international markets (5-10% maximum)"
                ],
                "resources": [
                    "Morningstar: Bond Investment Guide",
                    "Vanguard: Conservative Investment Strategies"
                ]
            },
            "moderate": {
                "advice": [
                    "Maintain a balanced portfolio (50-60% stocks, 40-50% bonds)",
                    "Diversify across domestic and international investments",
                    "Consider adding REITs for real estate exposure (5-10%)",
                    "Rebalance your portfolio annually"
                ],
                "resources": [
                    "Schwab: Modern Portfolio Theory Guide",
                    "Fidelity: Asset Allocation Strategies"
                ]
            },
            "aggressive": {
                "advice": [
                    "Higher allocation to stocks (70-90%) with focus on growth",
                    "Consider emerging markets and small-cap investments",
                    "Add alternative investments like commodities or real estate",
                    "Maintain discipline during market volatility"
                ],
                "resources": [
                    "Investopedia: Growth Investing Strategy",
                    "JP Morgan: Guide to Market Volatility"
                ]
            }
        },
        "retirement": {
            "conservative": {
                "advice": [
                    "Maximize contributions to tax-advantaged accounts (401(k), IRA)",
                    "Focus on capital preservation with bonds and stable value funds",
                    "Consider guaranteed income products like annuities",
                    "Plan for healthcare costs with HSA contributions"
                ],
                "resources": [
                    "AARP: Retirement Planning Guide",
                    "Social Security Administration: Benefits Planner"
                ]
            },
            "moderate": {
                "advice": [
                    "Maximize tax-advantaged retirement contributions",
                    "Maintain a balanced portfolio that shifts conservative with age",
                    "Consider Roth conversions for tax diversification",
                    "Review your retirement income plan regularly"
                ],
                "resources": [
                    "IRS: Retirement Plans FAQs",
                    "Vanguard: Retirement Income Calculator"
                ]
            },
            "aggressive": {
                "advice": [
                    "Maximize retirement account contributions and consider backdoor Roth options",
                    "Maintain higher equity allocation even in retirement",
                    "Consider self-directed retirement accounts for alternative investments",
                    "Develop a dynamic withdrawal strategy"
                ],
                "resources": [
                    "Fidelity: Retirement Income Planning",
                    "Morningstar: Sustainable Withdrawal Rates"
                ]
            }
        }
    }
    
    # Check if we have advice for the requested topic
    if topic_normalized in advice_db:
        advice_content = advice_db[topic_normalized][risk_profile_normalized]
        
        # If tool_context is provided, update state
        if tool_context:
            # Track topics the user has asked about
            advice_topics = tool_context.state.get("financial_advice_topics", [])
            if topic_normalized not in advice_topics:
                advice_topics.append(topic_normalized)
                tool_context.state["financial_advice_topics"] = advice_topics
            
            # Save user's risk profile for future reference
            tool_context.state["user_risk_profile"] = risk_profile_normalized
            
            print(f"--- Tool: Updated state with financial advice topics and risk profile ---")
        
        result = {
            "status": "success",
            "topic": topic,
            "risk_profile": risk_profile,
            "advice": advice_content["advice"],
            "resources": advice_content["resources"]
        }
        return result
    else:
        # Topic not found
        supported_topics = list(advice_db.keys())
        return {
            "status": "error",
            "error_message": f"Sorry, I don't have advice on '{topic}'. Available topics: {', '.join(supported_topics)}"
        }