export const AGENT_CONFIGS = {
  stock: {
    id: "stock",
    title: "Multi-Agent Equity Research",
    description:
      "A production-grade LangGraph system with modular agents that coordinate to research, analyze, and generate comprehensive investment reports.",
    tags: ["Company Intel", "News & Sentiment", "Fundamentals", "Valuation", "Risk Analysis"],
    status: "Live",
    gradient: "from-emerald-500 to-cyan-500",
    workflow: [
      { id: "company", name: "Company Intelligence Agent", icon: "🏢", status: "idle" },
      { id: "news", name: "News Research Agent", icon: "📰", status: "idle" },
      { id: "market", name: "Market Data Agent", icon: "📊", status: "idle" },
      { id: "fundamental", name: "Fundamental Analysis Agent", icon: "📈", status: "idle" },
      { id: "valuation", name: "Valuation Agent", icon: "💰", status: "idle" },
      { id: "risk", name: "Risk Analysis Agent", icon: "⚠️", status: "idle" },
      { id: "analyst", name: "Analyst Consensus Agent", icon: "🎯", status: "idle" },
      { id: "decision", name: "Investment Decision Agent", icon: "💡", status: "idle" },
    ],
    logs: [
      "Initializing LangGraph Multi-Agent system...",
      "Company Intelligence Agent researching...",
      "News Research Agent scanning...",
      "Market Data Agent fetching...",
      "Fundamental Analysis Agent calculating...",
      "Valuation Agent assessing...",
      "Risk Analysis Agent evaluating...",
      "Analyst Consensus Agent gathering ratings...",
      "Investment Decision Agent synthesizing report...",
      "Analysis complete.",
    ],
    exchanges: ["NSE", "BSE", "NASDAQ", "NYSE"],
    analysisOptions: ["Comprehensive Report"],
    resultType: "stock",
  },
  resume: {
    id: "resume",
    title: "Resume Analyser & Reviewer",
    description:
      "Upload a resume and receive ATS scoring, skill-gap analysis, recruiter insights, and personalized recommendations.",
    tags: ["ATS Scanner", "Resume Parser", "Career Coach", "Skill Matcher"],
    status: "Live",
    gradient: "from-violet-500 to-purple-500",
    workflow: [
      { id: "parser", name: "Resume Parser Agent", icon: "📄", status: "idle" },
      { id: "ats", name: "ATS Scoring Agent", icon: "📊", status: "idle" },
      { id: "skill", name: "Skill Matching Agent", icon: "🎯", status: "idle" },
      { id: "grammar", name: "Grammar Review Agent", icon: "✍️", status: "idle" },
      { id: "coach", name: "Career Coach Agent", icon: "👔", status: "idle" },
    ],
    logs: [
      "Reading resume...",
      "Extracting information...",
      "Calculating ATS score...",
      "Checking formatting...",
      "Matching skills...",
      "Finding improvement areas...",
      "Generating recommendations...",
      "Review complete.",
    ],
    experienceLevels: ["Fresher", "Intermediate", "Experienced"],
    resultType: "resume",
  },
};

export function generateMockResults(type) {
  if (type === "stock") {
    return {
      stockName: "Reliance Industries",
      symbol: "RELIANCE",
      exchange: "NSE",
      currentPrice: 2856.75,
      valuation: {
        "Current Price": 2856.75,
        "Trailing PE": 28.5,
        "Forward PE": 22.3,
        "EV/EBITDA": 16.8,
        "Assessment": "Fairly Valued"
      },
      change: 2.34,
      rsi: 62.4,
      macd: "Bullish",
      sentiment: "Positive",
      risk: "Moderate",
      recommendation: "BUY",
      confidence: 78,
      chartData: Array.from({ length: 24 }, (_, i) => ({
        time: `${i}:00`,
        value: 2800 + Math.sin(i * 0.5) * 60 + Math.random() * 20,
      })),
      signalData: Array.from({ length: 20 }, (_, i) => ({
        name: `P${i + 1}`,
        signals: Math.random() * 100,
        trend: 30 + Math.sin(i * 0.8) * 25 + Math.random() * 10,
      })),
    };
  }
  if (type === "resume") {
    return {
      atsScore: 72,
      skillMatch: 65,
      strengths: [
        "Strong technical background in Python",
        "Good project portfolio",
        "Clear career progression",
      ],
      weaknesses: [
        "Missing key certifications",
        "Weak action verbs used",
        "Formatting inconsistencies",
      ],
      missingSkills: ["Docker", "Kubernetes", "CI/CD", "GraphQL"],
      suggestions: [
        "Add quantifiable achievements",
        "Include a professional summary",
        "Optimize for ATS keywords",
      ],
    };
  }
  return {};
}
