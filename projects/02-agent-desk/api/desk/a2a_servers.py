"""A2A server implementations for individual agents."""

from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pathlib import Path
import uvicorn
import asyncio

from .config import settings
from .models import AgentCard, AgentType


class AgentA2AServer:
    """Base A2A server for an agent."""
    
    def __init__(self, agent_type: AgentType, port: int, 
                 description: str, capabilities: list):
        self.agent_type = agent_type
        self.port = port
        self.description = description
        self.capabilities = capabilities
        self.app = FastAPI(title=f"{agent_type.value.title()} Agent A2A Server")
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup A2A routes."""
        
        @self.app.get("/.well-known/agent-card.json")
        async def get_agent_card() -> AgentCard:
            """Return agent card for A2A discovery."""
            return AgentCard(
                name=f"{self.agent_type.value}_agent",
                description=self.description,
                capabilities=self.capabilities,
                tools=[
                    {
                        "name": f"analyze_{self.agent_type.value}",
                        "description": f"Perform {self.agent_type.value} analysis",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "ticker": {"type": "string"},
                                "question": {"type": "string"}
                            },
                            "required": ["ticker"]
                        }
                    }
                ],
                endpoints={
                    "analyze": f"/analyze",
                    "health": "/health"
                }
            )
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "agent": self.agent_type.value}
        
        @self.app.post("/analyze")
        async def analyze(request: Dict[str, Any]):
            """Perform analysis (placeholder - would integrate with actual agents)."""
            ticker = request.get("ticker")
            question = request.get("question", "Analyze this ticker")
            
            if not ticker:
                raise HTTPException(status_code=400, detail="Ticker is required")
            
            # In production, this would call the actual agent
            return {
                "agent": self.agent_type.value,
                "ticker": ticker,
                "status": "completed",
                "message": f"{self.agent_type.value.title()} analysis would be performed here"
            }
    
    async def start(self):
        """Start the A2A server."""
        config = uvicorn.Config(
            self.app,
            host="0.0.0.0",
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


class A2AServerManager:
    """Manages all A2A servers for agents."""
    
    def __init__(self):
        self.servers = {}
        self._create_servers()
    
    def _create_servers(self):
        """Create A2A servers for each agent."""
        
        agent_configs = [
            (
                AgentType.RESEARCH,
                settings.agent_base_port,  # 8201
                "Deep analysis of SEC filings using GraphRAG and Edgar MCP tools",
                ["sec_filing_analysis", "graph_rag_search", "edgar_mcp_integration"]
            ),
            (
                AgentType.MACRO,
                settings.agent_base_port + 1,  # 8202
                "Sector and macroeconomic analysis via news and market data",
                ["sector_analysis", "economic_indicators", "news_sentiment"]
            ),
            (
                AgentType.QUANT,
                settings.agent_base_port + 2,  # 8203
                "Technical analysis and quantitative metrics from price data",
                ["technical_analysis", "risk_metrics", "price_patterns"]
            ),
            (
                AgentType.RISK,
                settings.agent_base_port + 3,  # 8204
                "Risk assessment from integrated multi-agent analysis",
                ["risk_assessment", "position_sizing", "portfolio_impact"]
            ),
            (
                AgentType.SCRIBE,
                settings.agent_base_port + 4,  # 8205
                "Investment memo synthesis from all agent inputs",
                ["memo_writing", "investment_thesis", "recommendation_synthesis"]
            )
        ]
        
        for agent_type, port, description, capabilities in agent_configs:
            server = AgentA2AServer(agent_type, port, description, capabilities)
            self.servers[agent_type.value] = server
    
    async def start_all_servers(self):
        """Start all A2A servers in parallel."""
        if not settings.enable_a2a_servers:
            print("A2A servers disabled in configuration")
            return
        
        print("Starting A2A servers for all agents...")
        
        tasks = []
        for agent_name, server in self.servers.items():
            print(f"Starting {agent_name} agent A2A server on port {server.port}")
            tasks.append(asyncio.create_task(server.start()))
        
        # Run all servers concurrently
        await asyncio.gather(*tasks)
    
    def get_agent_cards(self) -> Dict[str, Dict[str, Any]]:
        """Get all agent cards for the main API to serve."""
        cards = {}
        
        for agent_name, server in self.servers.items():
            # Create agent card data (without actually starting the server)
            card = AgentCard(
                name=f"{agent_name}_agent",
                description=server.description,
                capabilities=server.capabilities,
                tools=[
                    {
                        "name": f"analyze_{agent_name}",
                        "description": f"Perform {agent_name} analysis",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "ticker": {"type": "string"},
                                "question": {"type": "string"}
                            },
                            "required": ["ticker"]
                        }
                    }
                ],
                endpoints={
                    "analyze": f"http://localhost:{server.port}/analyze",
                    "health": f"http://localhost:{server.port}/health",
                    "card": f"http://localhost:{server.port}/.well-known/agent-card.json"
                }
            )
            cards[agent_name] = card.model_dump()
        
        return cards


# Global A2A server manager
a2a_manager = A2AServerManager()


async def start_a2a_servers():
    """Start all A2A servers (used by start.sh)."""
    await a2a_manager.start_all_servers()


if __name__ == "__main__":
    """Run A2A servers directly."""
    asyncio.run(start_a2a_servers())