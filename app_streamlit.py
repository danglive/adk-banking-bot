# app_streamlit.py
import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import uuid
import os
import time
from datetime import datetime, timedelta
import altair as alt
from typing import Dict, Any, List, Optional, Union, Tuple
import asyncio
import aiohttp
import threading
from collections import defaultdict
import logging
import base64
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page configuration
st.set_page_config(
    page_title="Banking Assistant",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = 30  # seconds
REFRESH_INTERVAL = 10  # seconds for auto-refresh

# Application state
if 'user_id' not in st.session_state:
    st.session_state.user_id = f"streamlit_user_{uuid.uuid4().hex[:8]}"
if 'session_id' not in st.session_state:
    st.session_state.session_id = f"session_{uuid.uuid4().hex}"
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'metrics_data' not in st.session_state:
    st.session_state.metrics_data = {}
if 'historical_metrics' not in st.session_state:
    st.session_state.historical_metrics = []
if 'error' not in st.session_state:
    st.session_state.error = None
if 'tool_calls' not in st.session_state:
    st.session_state.tool_calls = defaultdict(int)
if 'token_usage' not in st.session_state:
    st.session_state.token_usage = {'in': 0, 'out': 0}
if 'active_tab' not in st.session_state:
    st.session_state.active_tab = "Chat"
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = time.time()

# Helper functions
def reset_conversation():
    """Reset the conversation history."""
    if 'messages' in st.session_state:
        st.session_state.messages = []
    # Generate a new session ID
    st.session_state.session_id = f"session_{uuid.uuid4().hex}"
    # Create a new session via API
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/sessions",
            json={
                "user_id": st.session_state.user_id,
                "session_id": st.session_state.session_id,
                "initial_state": {"source": "streamlit_ui"}
            },
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
    except Exception as e:
        st.error(f"Failed to create a new session: {str(e)}")
        logger.error(f"Session creation error: {str(e)}")
        st.session_state.error = str(e)

async def fetch_metrics_async():
    """Fetch metrics data asynchronously."""
    async with aiohttp.ClientSession() as session:
        try:
            # Fetch current metrics
            async with session.get(f"{API_BASE_URL}/health", timeout=API_TIMEOUT) as response:
                if response.status == 200:
                    metrics = await response.json()
                    st.session_state.metrics_data = metrics
                    st.session_state.last_refresh = time.time()
                    logger.info("Metrics data refreshed successfully")
                else:
                    logger.error(f"Failed to fetch metrics: {response.status}")

            # Fetch historical metrics if available
            async with session.get(f"{API_BASE_URL}/api/metrics/history", timeout=API_TIMEOUT) as response:
                if response.status == 200:
                    history = await response.json()
                    st.session_state.historical_metrics = history.get("data", [])
                    logger.info(f"Fetched {len(st.session_state.historical_metrics)} historical metrics records")
        except Exception as e:
            logger.error(f"Error fetching metrics: {str(e)}")
            # Don't update session state error to avoid interrupting the user experience

def format_message(msg):
    """Format message with appropriate styling."""
    if msg["role"] == "user":
        return f"You: {msg['content']}"
    else:
        return f"Assistant: {msg['content']}"

def create_line_chart(data, x_key, y_key, title, color_scheme='viridis'):
    """Create a line chart visualization."""
    if not data:
        return None
    
    df = pd.DataFrame(data)
    if x_key not in df.columns or y_key not in df.columns:
        return None
    
    fig = px.line(df, x=x_key, y=y_key, title=title)
    fig.update_layout(
        template="plotly_white",
        xaxis_title=x_key.replace('_', ' ').title(),
        yaxis_title=y_key.replace('_', ' ').title(),
        font=dict(family="Arial, sans-serif", size=12),
        height=400
    )
    return fig

def create_bar_chart(data, labels, values, title, color='lightblue'):
    """Create a bar chart visualization."""
    fig = go.Figure(data=[go.Bar(x=labels, y=values, marker_color=color)])
    fig.update_layout(
        title=title,
        template="plotly_white",
        xaxis_title="Category",
        yaxis_title="Count",
        font=dict(family="Arial, sans-serif", size=12),
        height=400
    )
    return fig

def fetch_session_state():
    """Fetch current session state from the API."""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/sessions/{st.session_state.user_id}/{st.session_state.session_id}",
            timeout=API_TIMEOUT
        )
        if response.status_code == 200:
            session_data = response.json()
            return session_data.get("state", {})
        else:
            logger.warning(f"Failed to fetch session state: {response.status_code}")
            return {}
    except Exception as e:
        logger.error(f"Error fetching session state: {str(e)}")
        return {}

def update_metrics_from_response(response_data):
    """Update local metrics based on the latest API response."""
    if not response_data:
        return
    
    # Update tool calls
    tool_calls = response_data.get("tool_calls", [])
    for tool_call in tool_calls:
        tool_name = tool_call.get("tool", "unknown")
        st.session_state.tool_calls[tool_name] += 1
    
    # Could also update token usage, latency, etc. if available in the response

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        color: #1E88E5 !important;
        margin-bottom: 0.5rem !important;
    }
    .sub-header {
        font-size: 1.25rem !important;
        font-weight: 400 !important;
        color: #424242 !important;
        margin-bottom: 2rem !important;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        font-size: 1rem;
        line-height: 1.5;
    }
    .user-message {
        background-color: #E3F2FD;
        border-left: 4px solid #1E88E5;
    }
    .assistant-message {
        background-color: #F5F5F5;
        border-left: 4px solid #616161;
    }
    .metrics-card {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #F8F9FA;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #1E88E5;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #616161;
    }
    .tab-content {
        padding: 1rem 0;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1rem;
    }
    div[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        font-size: 0.9rem;
        color: #616161;
    }
    .footer {
        margin-top: 3rem;
        text-align: center;
        color: #9E9E9E;
        font-size: 0.8rem;
    }
    .stButton button {
        background-color: #1E88E5;
        color: white;
        border-radius: 0.3rem;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .stButton button:hover {
        background-color: #1565C0;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://raw.githubusercontent.com/danglive/adk-banking-bot/main/logo/logo.png", width=200)
    st.markdown("### Banking Assistant Settings")
    
    # Authentication section
    auth_expander = st.expander("Authentication", expanded=not st.session_state.authenticated)
    with auth_expander:
        if not st.session_state.authenticated:
            auth_username = st.text_input("Username", "demo_user")
            auth_password = st.text_input("Password", "demo_password", type="password")
            
            if st.button("Login"):
                # In a real app, this would validate credentials against a database
                # For demo, accept any non-empty username/password
                if auth_username and auth_password:
                    st.session_state.authenticated = True
                    # Update session state via API
                    try:
                        response = requests.put(
                            f"{API_BASE_URL}/api/sessions/{st.session_state.user_id}/{st.session_state.session_id}",
                            json={
                                "user_id": st.session_state.user_id,
                                "session_id": st.session_state.session_id,
                                "state_updates": {"user_authenticated": True, "username": auth_username}
                            },
                            timeout=API_TIMEOUT
                        )
                        response.raise_for_status()
                        st.success("Login successful!")
                        auth_expander.expanded = False
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Authentication failed: {str(e)}")
                else:
                    st.warning("Please enter username and password")
        else:
            st.success("You are logged in")
            if st.button("Logout"):
                st.session_state.authenticated = False
                # Update session state via API
                try:
                    response = requests.put(
                        f"{API_BASE_URL}/api/sessions/{st.session_state.user_id}/{st.session_state.session_id}",
                        json={
                            "user_id": st.session_state.user_id,
                            "session_id": st.session_state.session_id,
                            "state_updates": {"user_authenticated": False}
                        },
                        timeout=API_TIMEOUT
                    )
                    response.raise_for_status()
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Logout failed: {str(e)}")
    
    # Session info
    st.markdown("### Session Information")
    st.info(f"User ID: {st.session_state.user_id[:8]}...")
    st.info(f"Session ID: {st.session_state.session_id[:8]}...")
    
    # Refresh metrics button
    if st.button("Refresh Metrics"):
        asyncio.run(fetch_metrics_async())
        st.success("Metrics refreshed!")
    
    # Clear conversation button
    if st.button("New Conversation"):
        reset_conversation()
        st.success("Started a new conversation!")
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("Auto-refresh metrics", value=True)
    
    # About section
    st.markdown("### About")
    st.markdown("""
    This Banking Assistant is built with Google's Agent Development Kit (ADK) 
    and Streamlit. It uses various LLMs like GPT-4o and Gemini to provide 
    intelligent banking assistance.
    """)
    
    # Footer
    st.markdown("""
    <div class="footer">
        ADK Banking Bot v1.0<br>
        © 2025 Your Bank
    </div>
    """, unsafe_allow_html=True)

# Main content
st.markdown('<h1 class="main-header">Banking Assistant</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Your AI-powered financial assistant</p>', unsafe_allow_html=True)

# Tabs for different sections
tabs = st.tabs(["💬 Chat", "📊 Analytics", "📝 Session State", "🔧 Tools"])

# Tab 1: Chat Interface
with tabs[0]:
    st.markdown("### Chat with Banking Assistant")
    
    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-message assistant-message">{message["content"]}</div>', unsafe_allow_html=True)
    
    # Input field for user message
    user_input = st.text_input("Type your message...", key="user_input")
    
    if user_input:
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Send the message to the Banking Bot API
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/chat",
                json={
                    "message": user_input,
                    "user_id": st.session_state.user_id,
                    "session_id": st.session_state.session_id
                },
                timeout=API_TIMEOUT
            )
            
            if response.status_code == 200:
                response_data = response.json()
                assistant_response = response_data.get("response_text", "I'm sorry, I couldn't process your request.")
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                
                # Update local metrics
                update_metrics_from_response(response_data)
                
                # Refresh metrics
                asyncio.run(fetch_metrics_async())
            else:
                st.error(f"Error: API returned status code {response.status_code}")
                logger.error(f"API error: {response.status_code} - {response.text}")
        except Exception as e:
            st.error(f"Failed to communicate with the Banking API: {str(e)}")
            logger.error(f"API communication error: {str(e)}")
            st.session_state.error = str(e)
        
        # Clear input field
        st.session_state.user_input = ""
        
        # Rerun to update the UI
        st.experimental_rerun()

# Tab 2: Analytics
with tabs[1]:
    st.markdown("### Banking Bot Analytics")
    
    # Metrics overview
    st.subheader("System Metrics")
    
    # Refresh metrics if needed
    if auto_refresh and time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
        asyncio.run(fetch_metrics_async())
    
    # Display metrics cards
    metrics_cols = st.columns(4)
    
    # Extract metrics from state
    metrics_data = st.session_state.metrics_data.get("config", {})
    current_metrics = st.session_state.metrics_data.get("status", "unknown")
    timestamp = st.session_state.metrics_data.get("timestamp", datetime.now().isoformat())
    
    with metrics_cols[0]:
        st.markdown(
            """
            <div class="metrics-card">
                <div class="metric-label">System Status</div>
                <div class="metric-value">""" + current_metrics + """</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    with metrics_cols[1]:
        st.markdown(
            """
            <div class="metrics-card">
                <div class="metric-label">Total Requests</div>
                <div class="metric-value">""" + str(len(st.session_state.messages) // 2) + """</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    with metrics_cols[2]:
        st.markdown(
            """
            <div class="metrics-card">
                <div class="metric-label">Last Updated</div>
                <div class="metric-value">""" + datetime.fromisoformat(timestamp).strftime("%H:%M:%S") + """</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    with metrics_cols[3]:
        st.markdown(
            """
            <div class="metrics-card">
                <div class="metric-label">Session Type</div>
                <div class="metric-value">""" + metrics_data.get("session_type", "unknown") + """</div>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    # Tool usage charts
    st.subheader("Tool Usage")
    
    if st.session_state.tool_calls:
        # Convert tool calls to dataframe
        tool_df = pd.DataFrame({
            "tool": list(st.session_state.tool_calls.keys()),
            "count": list(st.session_state.tool_calls.values())
        })
        
        # Create and display bar chart
        tool_fig = create_bar_chart(
            data=None,
            labels=list(st.session_state.tool_calls.keys()),
            values=list(st.session_state.tool_calls.values()),
            title="Tool Usage Count",
            color="#90CAF9"
        )
        st.plotly_chart(tool_fig, use_container_width=True)
    else:
        st.info("No tool usage data available. Try interacting with the chat!")
    
    # Mock historical data visualizations
    st.subheader("Historical Performance")
    
    # Create mock data if no real data available
    if not st.session_state.historical_metrics:
        # Mock data for demo purposes
        dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7, 0, -1)]
        mock_data = []
        for date in dates:
            mock_data.append({
                "date": date,
                "requests": int(50 + 20 * (0.5 - (random.random() if 'random' in globals() else 0.5))),
                "success_rate": 0.92 + 0.08 * (0.5 - (random.random() if 'random' in globals() else 0.5)),
                "avg_latency": 150 + 50 * (0.5 - (random.random() if 'random' in globals() else 0.5))
            })
        st.session_state.historical_metrics = mock_data
    
    # Create visualizations
    hist_cols = st.columns(2)
    
    with hist_cols[0]:
        # Request volume chart
        requests_fig = create_line_chart(
            data=st.session_state.historical_metrics,
            x_key="date",
            y_key="requests",
            title="Daily Request Volume",
            color_scheme="blues"
        )
        if requests_fig:
            st.plotly_chart(requests_fig, use_container_width=True)
    
    with hist_cols[1]:
        # Latency chart
        latency_fig = create_line_chart(
            data=st.session_state.historical_metrics,
            x_key="date",
            y_key="avg_latency",
            title="Average Response Latency (ms)",
            color_scheme="reds"
        )
        if latency_fig:
            st.plotly_chart(latency_fig, use_container_width=True)
    
    # Success rate chart
    success_fig = create_line_chart(
        data=st.session_state.historical_metrics,
        x_key="date",
        y_key="success_rate",
        title="Daily Success Rate",
        color_scheme="greens"
    )
    if success_fig:
        st.plotly_chart(success_fig, use_container_width=True)

# Tab 3: Session State
with tabs[2]:
    st.markdown("### Current Session State")
    
    # Fetch current session state
    session_state = fetch_session_state()
    
    if session_state:
        # Create a nicer view of the session state
        st.json(session_state)
        
        # Allow downloading session state as JSON
        json_str = json.dumps(session_state, indent=2)
        b64 = base64.b64encode(json_str.encode()).decode()
        href = f'<a href="data:application/json;base64,{b64}" download="session_state.json">Download Session State as JSON</a>'
        st.markdown(href, unsafe_allow_html=True)
    else:
        st.warning("No session state available or failed to fetch from API.")

# Tab 4: Tools
with tabs[3]:
    st.markdown("### Available Banking Tools")
    
    # Display available tools information
    tools_data = [
        {
            "name": "Get Account Balance",
            "description": "Fetches the current balance for a specified account.",
            "usage": "Ask about your balance in checking, savings, or other accounts.",
            "example": "What's my checking account balance?"
        },
        {
            "name": "Transfer Money",
            "description": "Transfers funds between accounts.",
            "usage": "Specify source account, destination account, and amount.",
            "example": "Transfer $100 from my checking to my savings account."
        },
        {
            "name": "Financial Advisor",
            "description": "Provides financial advice on various topics.",
            "usage": "Ask for advice on savings, investments, or retirement planning.",
            "example": "What's a good investment strategy for a moderate risk profile?"
        }
    ]
    
    for tool in tools_data:
        with st.expander(f"{tool['name']}"):
            st.markdown(f"**Description:** {tool['description']}")
            st.markdown(f"**Usage:** {tool['usage']}")
            st.markdown(f"**Example:** *{tool['example']}*")
    
    # Tool execution history
    st.subheader("Recent Tool Executions")
    
    if st.session_state.tool_calls:
        tool_history = []
        for tool, count in st.session_state.tool_calls.items():
            for i in range(count):
                # This would normally be real data from the API
                tool_history.append({
                    "tool": tool,
                    "timestamp": (datetime.now() - timedelta(minutes=i*5)).strftime("%H:%M:%S"),
                    "status": "Success" if random.random() > 0.1 else "Error" if 'random' in globals() else "Success"
                })
        
        tool_history_df = pd.DataFrame(tool_history)
        st.dataframe(tool_history_df, use_container_width=True)
    else:
        st.info("No tool execution history available yet. Try interacting with the chat!")

# Error handling
if st.session_state.error:
    st.error(f"Error: {st.session_state.error}")
    if st.button("Clear Error"):
        st.session_state.error = None
        st.experimental_rerun()

# Automatic refresh
if auto_refresh and time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
    # Use threading to avoid blocking the UI
    refresh_thread = threading.Thread(target=lambda: asyncio.run(fetch_metrics_async()))
    refresh_thread.daemon = True
    refresh_thread.start()
