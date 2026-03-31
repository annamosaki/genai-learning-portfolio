# LLM Foundation Ladder Demo

An interactive Next.js application demonstrating 12 progressive levels of Large Language Model capabilities, from basic stateless responses to advanced agent architectures with MCP integration.

## Features

- **12 Progressive Levels**: Explore LLM capabilities from stateless to agent-MCP
- **Interactive Chat**: Test each level with real-time responses
- **Advanced Inspector**: View prompts, chunks, reranking, graphs, security, agent steps, and metrics
- **Compare Mode**: Side-by-side comparison of different levels
- **Evaluation Board**: Performance metrics and benchmarking
- **Modern UI**: Dark theme with smooth animations and responsive design

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## Configuration

The app supports zone-based deployment through environment variables:

- `ZONE_BASE_PATH`: Base path for the application (default: "")
- `LAB_API_URL`: Backend API URL (default: "http://localhost:8100")

## API Integration

The application expects a backend API at the configured `LAB_API_URL` with the following endpoints:

- `GET /api/levels`: List of available levels
- `POST /api/chat`: Chat with specific level
- `GET /api/evals`: Evaluation results

All API calls are proxied through Next.js rewrites for zone compatibility.

## Architecture

### Components

- **LadderRail**: Navigation for 12 levels with level selection
- **ChatPane**: Interactive chat interface with suggestions and history  
- **Inspector**: Multi-tab inspector showing trace data and metrics
- **GraphCanvas**: SVG visualization of knowledge graphs
- **EvalBoard**: Performance metrics and evaluation results

### Levels

1. **Stateless**: Basic LLM responses
2. **Memory**: Conversation history
3. **Full Context**: Optimal context windowing  
4. **Naive RAG**: Simple retrieval-augmented generation
5. **Smart RAG**: Intelligent chunking and embeddings
6. **Rerank RAG**: Advanced reranking
7. **Graph RAG**: Knowledge graph enhanced retrieval
8. **Secured**: Security controls and access management
9. **Evaluated**: Quality measurement and benchmarking
10. **Agent RAG**: Agentic retrieval strategies
11. **Agent Tools**: Function calling and tool integration
12. **Agent MCP**: Model Context Protocol capabilities

## Development

### Tech Stack

- **Framework**: Next.js 15 with App Router
- **UI**: Tailwind CSS with custom design tokens
- **Animations**: Framer Motion
- **Icons**: Lucide React
- **Fonts**: Syne, DM Sans, IBM Plex Mono
- **TypeScript**: Full type safety

### Design System

The app uses a custom dark theme with portfolio-inspired design tokens:

```css
--color-void: #05070b     /* Background */
--color-surface: #0b1018  /* Cards */
--color-panel: #111823    /* Panels */  
--color-text: #e8eef7     /* Primary text */
--color-muted: #8b9bb4    /* Secondary text */
--color-accent: #3dffb5   /* Primary accent */
--color-accent-2: #4cc9ff /* Secondary accent */
--color-line: rgba(148,163,184,0.14) /* Borders */
```

Utility classes include `.btn`, `.btn-primary`, `.chip`, and `.display` for consistent styling.

## License

MIT License - see LICENSE file for details.