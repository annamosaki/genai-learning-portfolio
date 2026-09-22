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
    "Seeking quantitative research, data science and AI engineering roles. Available for immediate start. Based in Lisbon.",
  location: "Lisbon, Portugal",
  email: "mosakianna@gmail.com",
  phone: "+33 7 64 69 59 33",
  links: {
    github: "https://github.com/annamosaki",
    linkedin: "https://www.linkedin.com/in/annamosaki",
    site: "https://annamosaki.com",
  },
  summary:
    "Quantitative researcher and data scientist, graduated from ENSAE Paris, with 16 months at BNP Paribas CIB building machine-learning models for trading-desk risk monitoring and NLP analysis of trader communications. Over the past year I built GenAI systems covering RAG/GraphRAG, multi-agent orchestration, MCP and LLM evals.",
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
    languages: ["Python", "SQL", "VBA", "C++", "R"],
    ml: ["scikit-learn", "TensorFlow", "PyTorch", "NLP", "Time Series", "pandas", "RAG/GraphRAG", "LLM agents"],
    finance: [
      "Anomaly detection",
      "Trading-desk risk monitoring",
      "Market-conduct surveillance",
      "ALM / Vega",
      "Derivatives pricing & hedging",
      "Risk management",
    ],
    tools: ["pydantic-ai", "MCP", "A2A", "FastAPI", "Next.js", "Cursor", "Claude Code"],
  },
  experience: [
    {
      company: "BNP Paribas CIB",
      role: "Quantitative Researcher – Data Scientist",
      location: "Paris, France",
      start: "Oct 2024",
      end: "Sep 2025",
      bullets: [
        "Research and production of ML/DL time-series anomaly-detection models with streaming inference across product families.",
        "Collaborated with traders to source data and iterate on the product; NLP analysis of trader communications for market-conduct surveillance; two-week training in the London office.",
        "Selected for the BNP Paribas CIB Graduate Programme in Quantitative Research.",
      ],
    },
    {
      company: "BNP Paribas CIB",
      role: "Quantitative Researcher – Data Scientist, Summer Intern",
      location: "Paris, France",
      start: "Jun 2024",
      end: "Sep 2024",
      bullets: [
        "Built and benchmarked deep-learning time-series anomaly-detection models on trading data.",
      ],
    },
    {
      company: "Les Associations Mutuelles Le Conservateur",
      role: "ALM Modeling Intern",
      location: "Paris, France",
      start: "Jun 2023",
      end: "Aug 2023",
      bullets: [
        "Modeled portfolio Vega sensitivities in VBA; automated recurring financial simulations for the investment team.",
      ],
    },
  ] satisfies Experience[],
  education: [
    {
      school: "ENSAE Paris – Institut Polytechnique de Paris",
      degree: "Engineer's Degree (Diplôme d'Ingénieur) – Master's Degree, Finance and Data Science",
      location: "France",
      years: "2023 – 2025",
      notes: [
        "Coursework: Stochastic Calculus, Time Series, Advanced Machine Learning, ML for NLP, ML for Finance, Derivatives Pricing & Hedging, Risk Management, Green Finance, Banking Law.",
      ],
    },
    {
      school: "Université Paris-Saclay",
      degree: "Bachelor's Degree in Mathematics and Economics (Double Degree) – Graduated with Honors",
      location: "France",
      years: "2020 – 2023",
    },
    {
      school: "École Polytechnique Fédérale de Lausanne (EPFL)",
      degree: "Undergraduate studies in Mathematics",
      location: "Switzerland",
      years: "2018 – 2020",
    },
  ] satisfies Education[],
  wins: [
    {
      title: "1st Place",
      org: "GenAI Hackathon — AWS × Sia Partners × Mistral × Gide",
      detail: "RAG system for legal-document drafting.",
    },
    {
      title: "1st Place",
      org: "H-W3B Hackathon — Sia Partners × Tezos",
      detail: "Blockchain-secured digital passport for vehicles.",
    },
    {
      title: "Best End-of-Studies Finance Internship Prize",
      org: "ENSAE Paris",
      detail: "Awarded for the BNP Paribas CIB quantitative research internship.",
    },
  ] satisfies Win[],
  priorProjects: [
    "LLM Foundations: 12-level GenAI system — prompts → GraphRAG → evals, agents, MCP (Python, pydantic-ai).",
    "Agent Desk: multi-agent investment desk (research/macro/quant/risk/scribe) with FastA2A, HITL gates and dual MCP.",
    "Research Digest: ArXiv + fund/quant RSS desk for time-series × finance research.",
  ],
  activities: [
    {
      title: "Forum ENSAE — Communication Manager",
      period: "Sep 2023 – Mar 2024",
      detail:
        "Conferences with executives from Citadel, Société Générale, Crédit Agricole and INSEE.",
    },
    {
      title: "Georgian Caucasian Dance",
      period: "10 years",
      detail: "Competition dancer; diploma as official trainer.",
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
      repoUrl:
        "https://github.com/annamosaki/genai-learning-portfolio/tree/main/projects/01-llm-lab",
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
      repoUrl:
        "https://github.com/annamosaki/genai-learning-portfolio/tree/main/projects/02-agent-desk",
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
      repoUrl:
        "https://github.com/annamosaki/genai-learning-portfolio/tree/main/projects/03-research-digest",
    },
  ] satisfies ProjectMeta[],
} as const;

export type CV = typeof cv;
