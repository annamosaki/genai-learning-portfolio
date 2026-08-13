# Anna Mosaki — Portfolio

Responsive CV / portfolio site for Anna Mosaki, with live demo zones.

## Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS v4 (multi-zone)
- **API**: FastAPI (Ask Anna + project gateways)
- **Demos**: LLM Lab, Agent Desk, Research Digest

## Quick start

```bash
./start.sh
```

Profiles:

```bash
./start.sh --portfolio   # site + Ask Anna API
./start.sh --lab         # LLM Foundations demo only
./start.sh --desk        # Agent Desk demo only
./start.sh --digest      # Research Digest demo only
```

| Surface | URL |
|---------|-----|
| Portfolio | http://localhost:3000 |
| LLM Lab zone | http://localhost:3000/demos/llm-lab |
| Agent Desk zone | http://localhost:3000/demos/agent-desk |
| Research Digest | http://localhost:3000/demos/research-digest |
| Portfolio API | http://localhost:8000/docs |
| Lab API | http://localhost:8100/docs |
| Desk API | http://localhost:8200/docs |
| Digest API | http://localhost:8300/docs |

## Content

Single source of truth: `content/cv.ts` (experience, education, wins, live projects).

## Projects

Self-contained folders under `projects/` — each can be lifted into its own GitHub repo. Locally they run together via `Procfile` + honcho and are reachable under the portfolio domain through Next.js Multi Zones.

## Live

- Site: [annamosaki.com](https://annamosaki.com)
- Source: [github.com/annamosaki/genai-learning-portfolio](https://github.com/annamosaki/genai-learning-portfolio)

## Deploy

See [infra/DEPLOY.md](infra/DEPLOY.md). Everyday loop:

```bash
git add -A && git commit -m "your change"
./scripts/push-deploy.sh
```

## License

Private portfolio — all rights reserved.
