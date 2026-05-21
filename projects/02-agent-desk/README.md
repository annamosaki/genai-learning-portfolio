# Agent Desk

Multi-agent investment analysis desk with FastA2A orchestration, live SSE visualization, HITL approval gates, and dual MCP integration (Edgar + Yahoo Finance).

## 🎯 Overview

Agent Desk is a sophisticated multi-agent system for investment analysis that combines:

- **5 Specialized Agents**: Research, Macro, Quantitative, Risk, and Scribe agents
- **FastA2A Protocol**: Agent-to-Agent communication with optional separate servers
- **Human-in-the-Loop**: Approval gates for plan and memo review
- **Live Visualization**: Real-time agent graph and event timeline
- **MCP Integration**: Edgar Tools (HTTP) and Yahoo Finance (stdio) connectors
- **RAG-Powered Research**: GraphRAG search through SEC filings corpus

## 🏗️ Architecture

```
projects/02-agent-desk/
├── api/                    # FastAPI backend (port 8200)
│   ├── desk/
│   │   ├── agents/         # 5 specialized agents
│   │   ├── rag/           # RAG components from LLM Lab
│   │   ├── orchestrator.py # Main coordination logic
│   │   ├── events.py      # SSE event system
│   │   ├── hitl.py        # Human approval gates
│   │   ├── a2a_servers.py # Optional A2A servers
│   │   └── app.py         # FastAPI application
│   └── data/
│       ├── index/         # RAG index files (copied from LLM Lab)
│       ├── prices/        # Synthetic OHLCV data
│       └── replay/        # Demo replay events
├── web/                   # Next.js frontend (port 3200)
└── start.sh              # Unified startup script
```

## 🤖 Agents

### 1. Research Agent
- **Purpose**: Deep SEC filing analysis
- **Data Sources**: GraphRAG search, Edgar MCP tools
- **Outputs**: Fundamental strength assessment, key risk factors

### 2. Macro Agent  
- **Purpose**: Sector dynamics and economic environment
- **Data Sources**: News sentiment, economic indicators, Yahoo MCP
- **Outputs**: Macro context, sector positioning

### 3. Quantitative Agent
- **Purpose**: Technical analysis and statistical metrics  
- **Data Sources**: Historical price data (CSV files)
- **Outputs**: Technical indicators (RSI, MACD, Bollinger), risk metrics

### 4. Risk Agent
- **Purpose**: Integrated risk assessment
- **Inputs**: All other agent outputs
- **Outputs**: Multi-dimensional risk scoring, position sizing recommendations

### 5. Scribe Agent
- **Purpose**: Investment memo synthesis
- **Inputs**: All agent analyses  
- **Outputs**: Structured investment recommendation with price targets

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- OpenAI API key (optional - NVDA replay works without)

### Setup

1. **Clone and navigate**:
   ```bash
   cd projects/02-agent-desk/
   ```

2. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

3. **Start everything**:
   ```bash
   ./start.sh
   ```

4. **Open the app**:
   - Web Interface: http://localhost:3200
   - API Docs: http://localhost:8200/docs

### Demo Mode (No API Key)

Try the demo with ticker **NVDA** to see replay events without requiring an OpenAI API key.

## 📊 Features

### Live Visualization
- **Agent Graph**: SVG-based network showing agent status and communication
- **Event Timeline**: Real-time stream of agent activities and tool calls  
- **Approval Gates**: Interactive UI for human decision points

### Analysis Flow
1. **Plan Gate**: User approves the analysis approach
2. **Parallel Execution**: Research, Macro, and Quant agents run simultaneously
3. **Risk Assessment**: Risk agent processes all outputs
4. **Memo Creation**: Scribe agent synthesizes final recommendation
5. **Memo Gate**: User reviews final investment memo

### A2A Integration

#### In-Process Mode (Default)
- Agents run within main API process
- Emits A2A-shaped events for UI visualization
- Reliable and simple deployment

#### Server Mode (Optional)
Set `ENABLE_A2A_SERVERS=true` in `.env` to run each agent as separate A2A server:
- Research Agent: http://localhost:8201
- Macro Agent: http://localhost:8202  
- Quant Agent: http://localhost:8203
- Risk Agent: http://localhost:8204
- Scribe Agent: http://localhost:8205

Each exposes `/.well-known/agent-card.json` and analysis endpoints.

## 🔧 Configuration

### Environment Variables

```bash
# Required for live analysis
OPENAI_API_KEY=sk-your-key-here

# Edgar MCP identity (required by SEC)
EDGAR_IDENTITY="Your App Name (email@example.com)"

# Server ports
API_PORT=8200
WEB_PORT=3200

# A2A mode
ENABLE_A2A_SERVERS=false  # true for separate servers
AGENT_BASE_PORT=8201      # base port for A2A servers
```

### Data Sources

#### Price Data
Synthetic OHLCV data for NVDA, AAPL, MSFT in `data/prices/`. 
Generated with realistic volatility clustering and momentum patterns.

#### RAG Index
Copied from LLM Lab: `chunks.json`, `figures.json`, `graph.json`, `communities.json`.
Enables GraphRAG search through SEC filing corpus.

#### Replay Data
Complete NVDA analysis timeline in `data/replay/run-nvda.json` with ~25 events including approval gates.

## 🔌 MCP Integration

### Edgar Tools (HTTP MCP)
```python
# Simulated in current implementation
edgar_data = {
    "latest_10k": "Recent 10-K analysis...",
    "recent_8k": "Key 8-K filings...", 
    "insider_trading": "Recent insider activity..."
}
```

### Yahoo Finance (stdio MCP)  
```python
# Graceful fallback to local price data
if yfmcp_available:
    price_data = await yfmcp.get_historical_data(ticker)
else:
    price_data = load_local_csv(ticker)
```

## 📡 API Endpoints

### Core Endpoints
- `POST /api/run` - Start new analysis
- `GET /api/run/{id}/stream` - SSE event stream
- `POST /api/run/{id}/approve` - Approve/deny gates
- `GET /api/run/{id}` - Get run status

### Agent Discovery
- `GET /api/agents` - List all agents
- `GET /api/agents/cards` - A2A agent cards

### Health & Status
- `GET /api/health` - Service health
- `GET /` - API info

## 🧪 Testing & Verification

### Manual Verification

1. **Import test**:
   ```bash
   cd api
   source venv/bin/activate
   export PYTHONPATH="${PWD}:${PYTHONPATH}"
   python -c "from desk.app import app; print('✅ Import successful')"
   ```

2. **Replay test**:
   ```bash
   curl -X POST http://localhost:8200/api/run \
     -H "Content-Type: application/json" \
     -d '{"ticker": "NVDA"}'
   ```

3. **Web build test**:
   ```bash
   cd web
   npm run build
   ```

### Expected Behavior

#### Without OpenAI API Key
- NVDA ticker → Replay mode with simulated events
- Other tickers → Error message requesting API key
- All UI components render correctly

#### With OpenAI API Key
- Live agent execution with real LLM calls
- Actual RAG search and analysis
- Full approval gate workflow

## 🚨 Troubleshooting

### Common Issues

**Port conflicts**:
```bash
lsof -i :8200  # Check API port
lsof -i :3200  # Check web port
```

**Python path issues**:
```bash
export PYTHONPATH="${PWD}/api:${PYTHONPATH}"
```

**Missing dependencies**:
```bash
# API
cd api && pip install -r requirements.txt

# Web  
cd web && npm install
```

**A2A servers not starting**:
- Ensure `ENABLE_A2A_SERVERS=true` in `.env`
- Check ports 8201-8205 are available
- Verify virtual environment is activated

## 🎛️ Customization

### Adding New Agents
1. Create agent class in `desk/agents/new_agent.py`
2. Add to orchestrator flow in `orchestrator.py`
3. Update A2A server manager in `a2a_servers.py`
4. Add to web UI agent list

### Custom MCP Integration
Replace simulated MCP calls with real implementations:
```python
# In agents/research.py
async def _edgar_search(self, run_id: str, ticker: str):
    if mcp_client_available:
        return await edgar_mcp.search_filings(ticker)
    else:
        return self._simulate_edgar_data(ticker)
```

### Custom RAG Sources
Add new data sources to `data/index/` and update `rag/store.py` to load them.

## 📝 License

This project is part of the Projects-AI-DS-Fin repository.

## 🤝 Contributing

1. Follow existing code patterns
2. Update tests for new features  
3. Maintain backwards compatibility
4. Document new configuration options

---

**Agent Desk** - Where AI agents collaborate to deliver investment insights.