export type Experience = {
  company: string;
  role: string;
  location: string;
  start: string;
  end: string;
  bullets: string[];
};

export type Education = {
  school: string;
  degree: string;
  location: string;
  years: string;
  notes?: string[];
};

export type ProjectMeta = {
  id: string;
  slug: string;
  number: string;
  title: string;
  tagline: string;
  status: "planned" | "live";
  stack: string[];
  comingSoon: string[];
  demoUrl?: string;
  repoUrl?: string;
};

export type Win = {
  title: string;
  org: string;
  detail: string;
};

export const cv = {
  name: "Anna Mosaki",
  title: "Quantitative Researcher · Data Scientist · AI Engineer",
  seeking:
    "Seeking a full-time role in quantitative research, data science, trading, or finance. Available for immediate start. Open to opportunities in the United States and Europe.",
  location: "Paris, France",
  email: "mosakianna@gmail.com",
  phone: "+33 7 64 69 59 33",
  links: {
    github: "https://github.com/annamosaki",
    linkedin: "https://www.linkedin.com/in/annamosaki",
    site: "https://annamosaki.com",
  },
  summary:
    "ENSAE-trained quantitative researcher with hands-on experience at BNP Paribas CIB. I build ML systems for markets — NLP, time series, and multi-agent AI — and ship them with clear methodology.",
  languages: [
    { code: "fr", label: "French", level: "native" },
    { code: "ru", label: "Russian", level: "native" },
    { code: "ku", label: "Kurdish", level: "native" },
    { code: "en", label: "English", level: "fluent" },
    { code: "pt", label: "Portuguese", level: "advanced" },
    { code: "es", label: "Spanish", level: "advanced" },
    { code: "de", label: "German", level: "limited" },
  ],
  skills: {
    languages: ["Python", "SQL", "C++", "R", "VBA", "TypeScript"],
    ml: ["scikit-learn", "TensorFlow", "PyTorch", "NLP", "Time Series", "LangChain", "LangGraph"],
    finance: [
      "Anomaly detection",
      "PnL monitoring",
      "ALM / Vega",
      "Derivatives",
      "Risk management",
      "Algorithmic trading",
    ],
    tools: ["FastAPI", "Next.js", "MCP", "A2A", "Excel", "LaTeX", "Streamlit"],
  },
  experience: [
    {
      company: "BNP Paribas CIB",
      role: "Quantitative Researcher – Data Scientist, GM Quantitative Research & Engineering (PnL)",
      location: "Paris, France",
      start: "Oct 2024",
      end: "Sep 2025",
      bullets: [
        "Built anomaly-detection models on financial time series, improving signal quality and monitoring for front-office trading desks.",
        "Partnered with quantitative and risk teams to translate model outputs into actionable risk-reduction recommendations.",
        "Contributed to an NLP pipeline analyzing trader communications, supporting compliance and market-intelligence workflows.",
      ],
    },
    {
      company: "BNP Paribas CIB",
      role: "Summer Intern, Quantitative Researcher – Data Scientist",
      location: "Paris, France",
      start: "Jun 2024",
      end: "Sep 2024",
      bullets: [
        "Developed and evaluated deep learning models for cross-asset pattern detection; improved accuracy of internal risk dashboards.",
        "Presented technical results to senior stakeholders through structured memos and executive-ready presentations.",
      ],
    },
    {
      company: "Les Associations Mutuelles Le Conservateur",
      role: "ALM Modeling Intern",
      location: "Paris, France",
      start: "Jun 2023",
      end: "Aug 2023",
      bullets: [
        "Quantified portfolio Vega sensitivities to inform asset allocation and asset-liability management strategy.",
        "Built Excel and VBA tools to automate financial simulations for the investment team.",
      ],
    },
  ] satisfies Experience[],
  education: [
    {
      school: "ENSAE Paris – Institut Polytechnique de Paris",
      degree: "Engineer's Degree – Master's Degree, Finance, Risk & Data",
      location: "France",
      years: "2023 – 2025",
      notes: [
        "Award: Best Internship Prize.",
        "Courses: Machine Learning for Finance, Time Series Forecasting, NLP, Stochastic Calculus, Risk Management, Derivatives Pricing and Hedging, Algorithmic Trading, Green Finance, Parallel Programming.",
      ],
    },
    {
      school: "Université Paris-Saclay",
      degree: "Bachelor's Degree, Mathematics & Economics",
      location: "France",
      years: "2020 – 2023",
    },
    {
      school: "École Polytechnique Fédérale de Lausanne (EPFL)",
      degree: "Undergraduate studies in Mathematics (2 years)",
      location: "Switzerland",
      years: "2018 – 2020",
      notes: [
        "Studied mathematics for two years at EPFL; did not complete a bachelor's degree there. Bachelor's degree later earned at Université Paris-Saclay.",
      ],
    },
  ] satisfies Education[],
  wins: [
    {
      title: "1st Place",
      org: "GenAI Hackathon — AWS, Mistral, Sia Partners, Gide",
      detail: "RAG system to automate legal document completion.",
    },
    {
      title: "1st Place",
      org: "H-W3B Hackathon — Sia Partners, Tezos",
      detail: "Blockchain-secured digital car passport in Solidity.",
    },
    {
      title: "Best Internship Prize",
      org: "ENSAE Paris",
      detail: "Recognized for quantitative research internship impact.",
    },
  ] satisfies Win[],
  priorProjects: [
    "Hi!ckathon (Hi! Paris, VINCI, L'Oréal, Schneider Electric, Capgemini, TotalEnergies): groundwater-level forecasting model.",
    "Greenwashing Detection (ENSAE): NLP + regression measuring impact of corporate communications on investor behavior.",
    "Energy Demand Forecasting (ENSAE): national electricity consumption forecasting for energy planning.",
    "Chat-Doc (ENSAE): RAG web app to extract insights from user-uploaded documents (Python, Chainlit).",
  ],
  activities: [
    {
      title: "Forum ENSAE — Communication Manager",
      period: "Sep 2023 – Mar 2024",
      detail:
        "Led professional events with executives from Société Générale, Crédit Agricole, Citadel, and INSEE. Managed partnerships, alumni engagement, and external communications.",
    },
  ],
  projects: [
    {
      id: "01",
      slug: "llm-foundations",
      number: "01",
      title: "LLM Foundations",
      tagline:
        "Climb a 12-rung ladder from a memoryless prompt to GraphRAG, evals, agents, and MCP — each step queryable live.",
      status: "live" as const,
      stack: ["Python", "pydantic-ai", "OpenAI", "GraphRAG", "MCP"],
      comingSoon: [
        "Stateless → memory → full-context → naive RAG",
        "Smart chunking, reranking, GraphRAG, security tiers",
        "Evals, tools, and dual MCP (EDGAR + Yahoo Finance)",
      ],
      demoUrl: "/demos/llm-lab",
      repoUrl: "https://github.com/annamosaki/llm-lab",
    },
    {
      id: "02",
      slug: "agent-desk",
      number: "02",
      title: "Agent Desk",
      tagline:
        "Multi-agent investment desk over FastA2A — live graph of agent traffic with human approval gates.",
      status: "live" as const,
      stack: ["pydantic-ai", "FastA2A", "MCP", "FastAPI", "SSE"],
      comingSoon: [
        "Research / macro / quant / risk / scribe agents",
        "Live A2A message graph + HITL plan and memo gates",
        "EdgarTools + yfinance MCP split across specialists",
      ],
      demoUrl: "/demos/agent-desk",
      repoUrl: "https://github.com/annamosaki/agent-desk",
    },
    {
      id: "03",
      slug: "research-digest",
      number: "03",
      title: "Research Digest",
      tagline:
        "Live ArXiv + fund/quant RSS digest on time series × finance — free sources, SSE regenerate.",
      status: "live" as const,
      stack: ["ArXiv", "RSS", "FastAPI", "SSE", "Next.js"],
      comingSoon: [
        "ArXiv + curated fund/quant RSS (free forever)",
        "Papers / News / Fund research sections with citations",
        "SSE progress + one-click regenerate",
      ],
      demoUrl: "/demos/research-digest",
    },
    {
      id: "04",
      slug: "sentiment-bench",
      number: "04",
      title: "Sentiment Bench",
      tagline: "Financial NLP benchmark: FinBERT vs LSTM vs local LLM — accuracy, latency, and alpha.",
      status: "planned" as const,
      stack: ["PyTorch", "FinBERT", "LLM", "backtest"],
      comingSoon: [
        "Accuracy, F1, calibration (ECE)",
        "Latency and cost per 1k docs",
        "Downstream long/short Sharpe comparison",
      ],
    },
    {
      id: "05",
      slug: "forecast-bench",
      number: "05",
      title: "Forecast Bench",
      tagline: "Time-series foundation models on returns and volatility — purged walk-forward.",
      status: "planned" as const,
      stack: ["TimesFM", "Chronos-2", "Moirai", "statsforecast"],
      comingSoon: [
        "Returns & vol targets (not price levels)",
        "CRPS / MASE leaderboard",
        "Contamination-aware evaluation windows",
      ],
    },
  ] satisfies ProjectMeta[],
} as const;

export type CV = typeof cv;
