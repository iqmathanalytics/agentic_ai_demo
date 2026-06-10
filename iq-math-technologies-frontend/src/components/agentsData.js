export const AGENT_CONFIGS = {
  stock: {
    id: "stock",
    title: "Real-Time Stock Analyser",
    description:
      "Analyze stocks using market trends, technical indicators, sentiment signals, and AI-generated investment insights.",
    tags: ["Data Collector", "Technical Analysis", "Sentiment AI", "Risk Assessment"],
    status: "Live",
    gradient: "from-emerald-500 to-cyan-500",
    workflow: [
      { id: "collector", name: "Data Collector Agent", icon: "📊", status: "idle" },
      { id: "technical", name: "Technical Analysis Agent", icon: "📈", status: "idle" },
      { id: "sentiment", name: "Sentiment Analysis Agent", icon: "🧠", status: "idle" },
      { id: "risk", name: "Risk Assessment Agent", icon: "⚠️", status: "idle" },
      { id: "insight", name: "Investment Insight Agent", icon: "💡", status: "idle" },
    ],
    logs: [
      "Fetching stock data...",
      "Loading market history...",
      "Calculating RSI...",
      "Calculating MACD...",
      "Scanning sentiment signals...",
      "Evaluating risk...",
      "Generating AI report...",
      "Analysis complete.",
    ],
    exchanges: ["NSE", "BSE", "NASDAQ", "NYSE"],
    analysisOptions: ["Technical Analysis", "Fundamental Analysis", "Sentiment Analysis", "Risk Assessment"],
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
  linkedin: {
    id: "linkedin",
    title: "LinkedIn Profile Optimizer",
    description:
      "Review LinkedIn profiles and generate recommendations to improve visibility, engagement, and recruiter reach.",
    tags: ["Profile Audit", "SEO Score", "Recruiter Insights", "Optimization"],
    status: "Live",
    gradient: "from-blue-500 to-indigo-500",
    workflow: [
      { id: "scanner", name: "Profile Scanner", icon: "🔍", status: "idle" },
      { id: "keyword", name: "Keyword Optimizer", icon: "🔑", status: "idle" },
      { id: "visibility", name: "Recruiter Visibility Agent", icon: "👁️", status: "idle" },
      { id: "engagement", name: "Engagement Analyzer", icon: "📱", status: "idle" },
    ],
    logs: [
      "Scanning profile...",
      "Analyzing headline...",
      "Checking keywords...",
      "Evaluating visibility...",
      "Generating recommendations...",
      "Analysis complete.",
    ],
    resultType: "linkedin",
  },
};

export function generateMockResults(type) {
  if (type === "stock") {
    return {
      stockName: "Reliance Industries",
      symbol: "RELIANCE",
      exchange: "NSE",
      currentPrice: 2856.75,
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
  if (type === "linkedin") {
    return {
      profileScore: 58,
      visibilityScore: 45,
      headlineSuggestions: [
        "Add industry keywords to headline",
        "Include your value proposition",
        "Mention key technologies",
      ],
      keywordRecommendations: [
        "Add 'AI Engineering' to skills",
        "Include 'Agentic Systems' expertise",
        "Add 'MLOps' to your profile",
      ],
      tips: [
        "Optimize your about section",
        "Add more relevant experience",
        "Get endorsements for top skills",
        "Post regular content",
      ],
    };
  }
  return {};
}
