# ADK Banking Bot 🏦

![Dashboard](logo/dashboard.png)

## Overview

ADK Banking Bot is an intelligent banking assistant built using Google's Agent Development Kit (ADK). It leverages a multi-agent architecture to provide comprehensive banking services including account balance inquiries, money transfers, and financial advice.

This project demonstrates how to build enterprise-grade AI applications with ADK, featuring multiple specialized agents, security guardrails, persistent state management, and comprehensive monitoring.

## Features

- **Multi-Agent Architecture**: Specialized agents for different tasks (greetings, farewells, balance inquiries, transfers)
- **Advanced Security**: Input and tool execution guardrails to ensure secure banking operations
- **Session Management**: Persistent state tracking across conversations
- **Comprehensive Monitoring**: Real-time metrics, analytics, and performance tracking
- **Multiple UI Options**: REST API, WebSocket, Web Interface, and Streamlit Dashboard
- **Multi-Model Support**: Flexibility to use different LLMs (GPT-4o, Claude, Gemini) for different agents

## Architecture

The system follows a flowchart-based execution model:

```mermaid
flowchart TD
    %% Input Stage
    A([User Input 🧑‍💻]):::input --> B{{Root Banking Agent 🧠}}:::agent

    %% Safety Check
    B --> C1{{Check before_model_callback}}:::check
    C1 -- "Contains dangerous input 🚫" --> C2([Blocked  🔒]):::block
    C1 -- "Valid Input ✅" --> D{{Intent Detection}}:::intent

    %% Intent Routing
    D -- "Greeting 🙋‍♂️" --> G1([Greeting Agent🙋‍♂️ - say_hello 🤖]):::greet
    D -- "Farewell 👋" --> G2([Farewell Agent - say_goodbye 🤖]):::farewell
    D -- "Balance Inquiry 💰" --> F1([Get Balance 🏦]):::tool
    D -- "Transfer 💸" --> F2([Transfer Money 💳]):::tool
    D -- "Financial Advice 📊" --> F3([Finance Advisor 🧑‍🏫]):::tool

    %% Tool Callbacks
    F1 --> T1{{Check before_tool_callback 🔐}}:::check
    T1 -- "OK ✅" --> X1([Run Get Balance Tool ✅]):::run

    F2 --> T2{{Check before_tool_callback 🔐}}:::check
    T2 -- "Not authenticated or Over limit ❌" --> X2([Block  ⛔]):::block
    T2 -- "OK ✅" --> X3([Run Transfer Money  ✅]):::run

    %% Session Update
    X1 & X3 --> Z1([Update Session State 📝]):::session
    Z1 --> R1([Agent Responds and Saves Output Key 💬]):::respond

    %% Final response
    G1 & G2 & X2 & R1 --> Z([Final Response to User 📨]):::output

    %% Styles
    classDef input fill:#e3f2fd,stroke:#2196f3,stroke-width:2px
    classDef agent fill:#fff3e0,stroke:#fb8c00,stroke-width:2px
    classDef check fill:#ede7f6,stroke:#673ab7,stroke-width:2px
    classDef block fill:#ffebee,stroke:#e53935,stroke-width:2px
    classDef intent fill:#fffde7,stroke:#fdd835,stroke-width:2px
    classDef greet fill:#e0f7fa,stroke:#00acc1,stroke-width:2px
    classDef farewell fill:#f1f8e9,stroke:#7cb342,stroke-width:2px
    classDef tool fill:#e8f5e9,stroke:#43a047,stroke-width:2px
    classDef run fill:#f3e5f5,stroke:#9c27b0,stroke-width:2px
    classDef session fill:#ede7f6,stroke:#512da8,stroke-width:2px
    classDef respond fill:#e1f5fe,stroke:#0288d1,stroke-width:2px
    classDef output fill:#fffde7,stroke:#fbc02d,stroke-width:2px
```

## Project Structure

```
adk-banking-bot/
├── agents/                    # Agent definitions
│   ├── root_agent.py          # Main orchestrator agent
│   ├── greeting_agent.py      # Specialized greeting agent
│   ├── farewell_agent.py      # Specialized farewell agent
│   ├── balance_agent.py       # Balance inquiry agent
│   └── transfer_agent.py      # Money transfer agent
├── tools/                     # Banking tools implementations
│   ├── get_balance.py         # Account balance tool
│   ├── transfer_money.py      # Money transfer tool
│   └── finance_advisor.py     # Financial advice tool
├── callbacks/                 # Security guardrails
│   ├── before_model.py        # Input validation callbacks
│   └── before_tool.py         # Tool execution validation
├── sessions/                  # Session management
│   └── session_service.py     # Session state persistence
├── monitoring/                # Metrics and analytics
│   ├── metrics_collector.py   # Usage metrics collection
│   ├── analytics_service.py   # Data analysis and reporting
│   ├── performance_tracker.py # Performance monitoring
│   ├── alerts.py              # Alerting system
│   ├── logger.py              # Structured logging
│   └── usage_reporter.py      # Usage report generation
├── tests/                     # Comprehensive test suite
│   ├── test_agents/           # Tests for agent modules
│   ├── test_tools/            # Tests for tool implementations
│   ├── test_callbacks/        # Tests for security callbacks
│   ├── test_sessions/         # Tests for session management
│   ├── test_monitoring/       # Tests for monitoring system
│   └── test_api/              # Tests for API endpoints
├── app.py                     # FastAPI backend
├── app_streamlit.py           # Streamlit dashboard
├── runner.py                  # Agent orchestration
├── config.py                  # Configuration management
└── requirements.txt           # Dependencies
```

## Installation

1. Clone the repository
```bash
git clone https://github.com/danglive/adk-banking-bot.git
cd adk-banking-bot
```

2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure API keys
Create a `.env` file with your API keys:
```
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

## Running the Application

### FastAPI Backend

```bash
python app.py
```

Visit http://localhost:8000/ui for the simple web interface or http://localhost:8000/docs for API documentation.

### Streamlit Dashboard

```bash
streamlit run app_streamlit.py
```

Visit http://localhost:8501 for the interactive dashboard.

## Docker Deployment

Build and run the Docker container:

```bash
# Build the Docker image
docker build -t adk-banking-bot .

# Run the container
docker run -p 8000:8000 -p 8501:8501 --env-file .env adk-banking-bot
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
make test

# Run specific test modules
pytest tests/test_agents

# Generate coverage report
make coverage
```

## Monitoring & Analytics

The system includes extensive monitoring capabilities:

- **Real-time Metrics**: Request counts, latency, success rates
- **Usage Analytics**: Tool usage patterns, user behavior
- **Performance Tracking**: Response times, token usage
- **Alerting**: Automated alerts for anomalies and issues
- **Logging**: Structured logs for debugging and audit

## Key ADK Components

This project showcases several key ADK features:

1. **Multi-Agent System**: Root agent delegates to specialized sub-agents
2. **Tool Integration**: Banking functions as callable tools
3. **Session State**: Persistent conversation memory across turns
4. **Callbacks**: Pre-model and pre-tool safety checks
5. **Multi-Model Support**: Flexibility to use different LLMs

## Author

**Van Tuan Dang**  
Email: vantuandang1990@gmail.com  
GitHub: [danglive](https://github.com/danglive)

## Acknowledgments

- Google's Agent Development Kit (ADK) team
- OpenAI, Anthropic, and Google AI for their LLM APIs
- The Streamlit team for the amazing dashboard framework