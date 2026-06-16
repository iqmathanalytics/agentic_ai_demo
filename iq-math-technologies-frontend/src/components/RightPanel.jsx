import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useState, useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Brush,
} from "recharts";
import { AGENT_CONFIGS } from "./agentsData";

const statusIcons = {
  idle: "○",
  running: "◉",
  completed: "✓",
  failed: "✕",
};

const statusColors = {
  idle: "text-slate-500",
  running: "text-cyan-300",
  completed: "text-emerald-400",
  failed: "text-red-400",
};

const statusBg = {
  idle: "bg-slate-500/10 border-slate-500/20",
  running: "bg-cyan-500/15 border-cyan-500/35 shadow-[0_0_24px_-8px_rgba(34,211,238,0.7)]",
  completed: "bg-emerald-500/10 border-emerald-500/25",
  failed: "bg-red-500/10 border-red-500/25",
};

function LogLine({ text, isLatest }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -14 }}
      animate={{ opacity: 1, x: 0 }}
      className={`flex items-start gap-2 py-1 text-xs font-mono ${
        isLatest ? "text-cyan-200" : "text-slate-500"
      }`}
    >
      <span className="text-slate-600 shrink-0 select-none">{">"}</span>
      <span className="break-words">{text}</span>
      {isLatest && <span className="inline-block w-1.5 h-4 bg-cyan-300/70 animate-pulse ml-0.5" />}
    </motion.div>
  );
}

function WorkflowStep({ step, status, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className={`relative p-2.5 rounded-xl border transition-all duration-500 ${statusBg[status] || statusBg.idle}`}
    >
      {index > 0 && <div className="absolute -top-2.5 left-5 h-2.5 w-px bg-white/10" />}
      <div className="flex items-center gap-2.5">
        <div className={`w-7 h-7 rounded-lg border flex items-center justify-center text-[10px] ${
          status === "running" ? "border-cyan-500/50 bg-cyan-500/10" : "border-white/10 bg-black/30"
        }`}>
          {status === "running" ? (
            <motion.span
              animate={{ scale: [1, 1.15, 1], opacity: [0.65, 1, 0.65] }}
              transition={{ repeat: Infinity, duration: 1.1 }}
              className={statusColors.running}
            >
              {statusIcons.running}
            </motion.span>
          ) : (
            <span className={statusColors[status] || statusColors.idle}>{statusIcons[status] || statusIcons.idle}</span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className={`text-[11px] font-semibold truncate ${status === "idle" ? "text-slate-500" : "text-white"}`}>
            {step.name}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function ProgressBar({ progress }) {
  return (
    <div className="relative h-2.5 rounded-full bg-white/5 p-[2px] overflow-hidden border border-white/5">
      <motion.div
        className="h-full rounded-full bg-gradient-to-r from-cyan-500 via-indigo-500 to-emerald-400"
        initial={{ width: 0 }}
        animate={{ width: `${progress}%` }}
        transition={{ duration: 0.5, ease: "circOut" }}
      />
    </div>
  );
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-premium-bg border border-white/10 rounded-xl px-4 py-3 shadow-2xl backdrop-blur-md">
      <p className="text-slate-500 text-[10px] font-mono mb-1 uppercase tracking-tighter">{payload[0].payload.time}</p>
      <p className="text-cyan-400 text-sm font-bold font-mono">${Number(payload[0].value).toLocaleString()}</p>
    </div>
  );
}

const markdownComponents = {
  table: ({ children }) => (
    <div className="my-6 overflow-x-auto rounded-xl border border-white/10 bg-black/20">
      <table className="w-full min-w-[480px] border-collapse text-left text-[13px]">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-white/[0.04] border-b border-white/10">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-white/5">{children}</tbody>,
  tr: ({ children }) => <tr className="hover:bg-white/[0.02] transition-colors">{children}</tr>,
  th: ({ children }) => (
    <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-slate-400 whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-4 py-3 text-slate-300 align-top leading-relaxed">{children}</td>
  ),
  h3: ({ children }) => (
    <h3 className="text-base font-black text-cyan-400 mt-8 mb-3 first:mt-0">{children}</h3>
  ),
  h2: ({ children }) => (
    <h2 className="text-lg font-black text-violet-400 mt-8 mb-4 first:mt-0 border-b border-white/5 pb-2">{children}</h2>
  ),
  ul: ({ children }) => <ul className="space-y-2 my-4 list-none pl-0">{children}</ul>,
  li: ({ children }) => (
    <li className="flex items-start gap-2 text-slate-300">
      <span className="text-cyan-500 mt-1 shrink-0">•</span>
      <span className="flex-1">{children}</span>
    </li>
  ),
  p: ({ children }) => <p className="text-slate-300 leading-relaxed my-3">{children}</p>,
  strong: ({ children }) => <strong className="text-white font-bold">{children}</strong>,
};

function ReportBlock({ title, report }) {
  if (!report) return null;
  return (
    <div className="rounded-2xl bg-premium-bg border border-white/5 p-6 shadow-inner">
      <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-bold flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-gradient-to-r from-cyan-400 to-blue-500" />
        {title}
      </div>
      <div className="prose prose-invert prose-sm max-w-none prose-headings:text-cyan-400 prose-headings:font-black prose-p:text-slate-300 prose-li:text-slate-300 prose-strong:text-white">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {report}
        </ReactMarkdown>
      </div>
    </div>
  );
}

function AtsBreakdownTable({ rows }) {
  if (!rows?.length) return null;
  return (
    <div className="rounded-2xl bg-premium-bg border border-white/5 p-6 shadow-inner">
      <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-bold flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-gradient-to-r from-violet-400 to-purple-500" />
        ATS Compatibility Analysis
      </div>
      <div className="overflow-x-auto rounded-xl border border-white/10">
        <table className="w-full min-w-[520px] border-collapse text-left">
          <thead>
            <tr className="bg-white/[0.04] border-b border-white/10">
              <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-violet-400">Component</th>
              <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-violet-400 w-28">Score</th>
              <th className="px-4 py-3 text-[10px] font-black uppercase tracking-widest text-violet-400">Comments</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5">
            {rows.map((row) => {
              const pct = row.max ? Math.round((row.score / row.max) * 100) : 0;
              const tone =
                pct >= 75 ? "text-emerald-400" : pct >= 45 ? "text-amber-400" : "text-rose-400";
              return (
                <tr key={row.component} className="hover:bg-white/[0.02]">
                  <td className="px-4 py-4 text-sm font-semibold text-white whitespace-nowrap">{row.component}</td>
                  <td className={`px-4 py-4 text-sm font-black ${tone} whitespace-nowrap`}>
                    {row.score}/{row.max}
                  </td>
                  <td className="px-4 py-4 text-[13px] text-slate-400 leading-relaxed">{row.comment}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BulletRewriteCards({ items, role }) {
  if (!items?.length) return null;
  return (
    <div className="rounded-2xl bg-premium-bg border border-white/5 p-6 shadow-inner">
      <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-2 font-bold flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-gradient-to-r from-amber-400 to-orange-500" />
        Bullet Rewrite Examples
      </div>
      <p className="text-[12px] text-slate-500 mb-5">
        Transform data-focused bullets into impact-driven statements for {role || "your target role"}.
      </p>
      <div className="space-y-4">
        {items.map((item, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="grid md:grid-cols-2 gap-3"
          >
            <div className="p-4 rounded-xl bg-rose-500/[0.06] border border-rose-500/20">
              <div className="text-[10px] font-black uppercase tracking-widest text-rose-400 mb-2">Before</div>
              <p className="text-[13px] text-slate-300 leading-relaxed italic">&ldquo;{item.original}&rdquo;</p>
            </div>
            <div className="p-4 rounded-xl bg-emerald-500/[0.06] border border-emerald-500/20">
              <div className="text-[10px] font-black uppercase tracking-widest text-emerald-400 mb-2">
                {item.label || "After"}
              </div>
              <p className="text-[13px] text-slate-200 leading-relaxed">&ldquo;{item.revised}&rdquo;</p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function hasValue(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") {
    if (["", "N/A", "NA", "null", "undefined", "Data Not Available"].includes(value)) return false;
    return true;
  }
  if (typeof value === "number") {
    if (Number.isNaN(value)) return false;
    return true;
  }
  return true;
}

function formatValue(value, fmt) {
  if (!hasValue(value)) return null;
  if (typeof value === "number") {
    if (fmt === "currency") {
      return "$" + (Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2));
    }
    if (Math.abs(value) < 1 && value !== 0) {
      return (value * 100).toFixed(2).replace(/\.?0+$/, "") + "%";
    }
    if (value >= 1e12) return "$" + (value / 1e12).toFixed(2) + "T";
    if (value >= 1e9) return "$" + (value / 1e9).toFixed(2) + "B";
    if (value >= 1e6) return "$" + (value / 1e6).toFixed(2) + "M";
    return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
  }
  return String(value);
}

function MetricCard({ label, value, className, labelColor }) {
  return (
    <motion.div whileHover={{ y: -4 }} className={`p-6 rounded-2xl border shadow-lg ${className || ""}`}>
      <div className={`text-[10px] uppercase tracking-widest font-black mb-3 ${labelColor || "text-slate-500"}`}>{label}</div>
      <div className="text-3xl font-black text-white tracking-tighter">{value}</div>
    </motion.div>
  );
}

function StockResults({ data }) {
  const valuation = data.valuation || {};
  const fundamentals = data.fundamentals || {};
  const analystRatings = data.analystRatings || {};
  const recommendation = data.recommendation || {};
  const riskAnalysis = data.riskAnalysis || {};
  const bullishFactors = data.bullishFactors || [];
  const bearishFactors = data.bearishFactors || [];
  const newsItems = data.newsItems?.length
    ? data.newsItems
    : (data.latestNews || []).map((title) => ({ title, snippet: title, url: "", source: "", date: "" }));
  const rawChartData = data.chartData || [];
  const [chartRange, setChartRange] = useState("1Y");

  const currentPrice = data.currentPrice ?? valuation["Current Price"] ?? valuation["currentPrice"];
  const marketCap = data.marketCap ?? valuation["Market Cap"] ?? valuation["marketCap"];

  const chartData = useMemo(() => {
    if (!rawChartData.length) return [];
    const today = new Date().toISOString().slice(0, 10);
    const last = rawChartData[rawChartData.length - 1];
    if (currentPrice && last?.time !== today) {
      return [...rawChartData, { time: today, value: Number(currentPrice) }];
    }
    if (currentPrice && last?.time === today) {
      return [...rawChartData.slice(0, -1), { time: today, value: Number(currentPrice) }];
    }
    return rawChartData;
  }, [rawChartData, currentPrice]);

  const filteredChartData = useMemo(() => {
    if (!chartData.length) return [];
    const today = new Date();
    today.setHours(23, 59, 59, 999);
    const ranges = { "1M": 30, "6M": 180, "1Y": 365, "5Y": 1825, MAX: 99999 };
    const days = ranges[chartRange] || 365;
    const cutoff = new Date(today);
    cutoff.setDate(cutoff.getDate() - days);
    cutoff.setHours(0, 0, 0, 0);
    return chartData.filter((d) => {
      const dt = new Date(`${d.time}T12:00:00`);
      return dt >= cutoff && dt <= today;
    });
  }, [chartData, chartRange]);
  const targetPrice = analystRatings["Target Mean Price"];
  const consensusRating = analystRatings["Consensus Rating"];
  const recAction = recommendation.recommendation || recommendation.rating;
  const recConfidence = recommendation.confidence;

  const metricCards = [];

  if (hasValue(currentPrice) && currentPrice > 0) {
    metricCards.push({
      key: "price",
      label: "Current Price",
      value: formatValue(currentPrice, "currency"),
      className: "bg-gradient-to-br from-cyan-600/10 via-blue-600/5 to-transparent border-cyan-500/20",
      labelColor: "text-cyan-400",
    });
  }

  if (hasValue(marketCap)) {
    metricCards.push({
      key: "cap",
      label: "Market Cap",
      value: formatValue(marketCap),
      className: "bg-gradient-to-br from-sky-600/10 via-teal-600/5 to-transparent border-sky-500/20",
      labelColor: "text-sky-400",
    });
  }

  if (hasValue(recAction)) {
    metricCards.push({
      key: "rec",
      label: "Recommendation",
      value: (
        <>
          <div className="text-3xl font-black text-white tracking-tighter">{recAction}</div>
          {hasValue(recConfidence) && (
            <div className="text-[11px] text-slate-500 font-medium mt-2">Confidence: {recConfidence}%</div>
          )}
        </>
      ),
      className: "bg-gradient-to-br from-emerald-600/10 via-teal-600/5 to-transparent border-emerald-500/20",
      labelColor: "text-emerald-400",
    });
  }

  if (hasValue(targetPrice)) {
    metricCards.push({
      key: "target",
      label: "Analyst Target Price",
      value: (
        <>
          <div className="text-3xl font-black text-white tracking-tighter">{formatValue(targetPrice, "currency")}</div>
          {hasValue(consensusRating) && (
            <div className="text-[11px] text-slate-500 mt-2 leading-relaxed">
              Wall Street view: <span className="text-indigo-300 font-medium">{consensusRating}</span>
            </div>
          )}
        </>
      ),
      className: "bg-gradient-to-br from-indigo-600/10 via-purple-600/5 to-transparent border-indigo-500/20",
      labelColor: "text-indigo-400",
    });
  }

  const valuationFieldDefs = [
    { label: "Trailing PE", key: "Trailing PE" },
    { label: "Forward PE", key: "Forward PE" },
    { label: "PEG Ratio", key: "PEG Ratio" },
    { label: "EV/EBITDA", key: "EV/EBITDA" },
    { label: "Assessment", key: "Assessment" },
  ];
  const availableValuationFields = valuationFieldDefs
    .map((f) => ({ ...f, value: valuation[f.key] }))
    .filter((f) => hasValue(f.value));

  const fundamentalKeys = [
    "Revenue Growth", "Earnings Growth", "Gross Margin", "Operating Margin",
    "Net Margin", "ROE", "ROA", "Debt to Equity", "Current Ratio", "Free Cash Flow",
  ];
  const availableFundamentalFields = fundamentalKeys
    .map((key) => ({ key, data: fundamentals[key] }))
    .filter((f) => f.data && hasValue(f.data.Value));

  const analystFieldDefs = [
    { label: "Wall Street Consensus", key: "Consensus Rating" },
    { label: "Number of Analysts", key: "Number of Analyst Opinions" },
    { label: "Target High", key: "Target High Price", fmt: "currency" },
    { label: "Target Low", key: "Target Low Price", fmt: "currency" },
  ];
  const availableAnalystFields = analystFieldDefs
    .map((f) => ({ ...f, value: analystRatings[f.key] }))
    .filter((f) => hasValue(f.value));

  const riskFieldDefs = [
    { label: "Volatility", key: "Annual Volatility", suffix: "%" },
    { label: "Beta", key: "Beta" },
    { label: "Max Drawdown", key: "Maximum Drawdown", suffix: "%" },
    { label: "Risk Score", key: "Classification" },
  ];
  const availableRiskFields = riskFieldDefs
    .map((f) => ({ ...f, value: riskAnalysis[f.key] }))
    .filter((f) => hasValue(f.value));

  return (
    <div className="space-y-8">
      {(data.dataSources?.length > 0 || hasValue(data.dataCompleteness)) && (
        <div className="rounded-2xl bg-premium-bg border border-white/5 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
            <div className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Data Trust</div>
            {hasValue(data.dataCompleteness) && (
              <div className="text-[11px] text-cyan-400 font-semibold">{data.dataCompleteness}% data completeness</div>
            )}
          </div>
          {hasValue(data.dataCompleteness) && (
            <div className="h-2 rounded-full bg-white/5 mb-3 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-400 transition-all"
                style={{ width: `${Math.min(100, data.dataCompleteness)}%` }}
              />
            </div>
          )}
          {data.dataSources?.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {data.dataSources.map((src) => (
                <span key={src} className="px-2 py-1 text-[10px] rounded-lg bg-white/5 border border-white/10 text-slate-300">
                  {src}
                </span>
              ))}
            </div>
          )}
          <p className="text-[10px] text-slate-500 mt-3 leading-relaxed">
            Based on publicly available market data. Not financial advice. Verify before investing.
          </p>
        </div>
      )}

      {metricCards.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {metricCards.map((card) => (
            <MetricCard key={card.key} {...card} />
          ))}
        </div>
      )}

      {(recommendation.summary || recommendation.reasoning?.length || recommendation.reason1) && (
        <div className="rounded-2xl bg-gradient-to-br from-indigo-600/10 via-purple-600/5 to-transparent border border-indigo-500/20 p-6">
          <div className="text-[10px] text-indigo-400 uppercase tracking-widest mb-3 font-black flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-indigo-400" />
            REASON FOR RECOMMENDATION
          </div>
          {recommendation.summary && (
            <p className="text-sm text-white font-medium leading-relaxed mb-4">{recommendation.summary}</p>
          )}
          <div className="space-y-3">
            {(recommendation.reasoning?.length ? recommendation.reasoning : [recommendation.reason1, recommendation.reason2].filter(Boolean)).map((reason, idx) => (
              <div key={idx} className="flex items-start gap-3">
                <span className={`mt-0.5 text-sm shrink-0 font-bold ${
                  recAction === "BUY" ? "text-emerald-400" : recAction === "SELL" ? "text-rose-400" : "text-amber-400"
                }`}>
                  {idx + 1}.
                </span>
                <span className="text-[13px] text-slate-300 leading-relaxed">{reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {availableValuationFields.length > 0 && (
        <div className="rounded-2xl bg-premium-bg border border-white/5 p-6">
          <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-black">Valuation Metrics</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {availableValuationFields.map((f) => (
              <div key={f.key}>
                <div className="text-[10px] text-slate-500 mb-1">{f.label}</div>
                <div className="text-sm font-bold text-white">{formatValue(f.value)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {hasValue(data.companyOverview) && (
        <div className="rounded-2xl bg-premium-bg border border-white/5 p-6 shadow-inner">
          <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-bold flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-gradient-to-r from-cyan-400 to-blue-500" />
            Company Overview
          </div>
          <div className="prose prose-invert prose-sm max-w-none prose-p:text-slate-300 prose-p:leading-relaxed prose-strong:text-cyan-400">
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{data.companyOverview}</ReactMarkdown>
          </div>
        </div>
      )}

      {(bullishFactors.length > 0 || bearishFactors.length > 0) && (
        <div className={`grid gap-5 ${bullishFactors.length > 0 && bearishFactors.length > 0 ? "md:grid-cols-2" : ""}`}>
          {bullishFactors.length > 0 && (
            <ResultList title="Bullish Factors" items={bullishFactors} tone="text-emerald-400" marker="▲" />
          )}
          {bearishFactors.length > 0 && (
            <ResultList title="Bearish Factors" items={bearishFactors} tone="text-rose-400" marker="▼" />
          )}
        </div>
      )}

      {availableFundamentalFields.length > 0 && (
        <div className="rounded-2xl bg-premium-bg border border-white/5 p-6">
          <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-black">Fundamental Metrics</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {availableFundamentalFields.map((f) => (
              <div key={f.key}>
                <div className="text-[10px] text-slate-500 mb-1">{f.key}</div>
                <div className="text-sm font-bold text-white">
                  {formatValue(f.data.Value)}
                  {f.data.Classification && hasValue(f.data.Classification) && f.data.Classification !== "Data Not Available" && (
                    <span className={`ml-2 text-[10px] ${
                      f.data.Classification === "Strong" ? "text-emerald-400" :
                      f.data.Classification === "Weak" ? "text-rose-400" : "text-slate-400"
                    }`}>
                      {f.data.Classification}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {chartData.length > 0 && (
        <div className="rounded-2xl bg-premium-bg border border-white/5 p-6">
          <div className="flex items-center justify-between mb-5">
            <div className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Price Chart</div>
            <div className="flex gap-1">
              {["1M", "6M", "1Y", "5Y", "MAX"].map((r) => (
                <button
                  key={r}
                  onClick={() => setChartRange(r)}
                  className={`px-2.5 py-1 text-[10px] font-bold rounded-md transition-all ${
                    chartRange === r
                      ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                      : "text-slate-500 hover:text-slate-300 border border-transparent"
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={filteredChartData}>
              <defs>
                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22D3EE" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#22D3EE" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#64748B" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="value" stroke="#22D3EE" strokeWidth={2} fill="url(#colorValue)" />
              <Brush dataKey="time" height={30} stroke="#22D3EE" fill="#1A0A0E" travellerWidth={10} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {availableRiskFields.length > 0 && (
        <div className="rounded-2xl bg-premium-bg border border-white/5 p-6">
          <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-black">Risk Analysis</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {availableRiskFields.map((f) => (
              <div key={f.key}>
                <div className="text-[10px] text-slate-500 mb-1">{f.label}</div>
                <div className="text-sm font-bold text-white">
                  {f.key === "Classification" ? (
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                      String(f.value).toLowerCase() === "low" ? "bg-emerald-500/10 text-emerald-400" :
                      String(f.value).toLowerCase() === "high" ? "bg-rose-500/10 text-rose-400" :
                      "bg-amber-500/10 text-amber-400"
                    }`}>{f.value}</span>
                  ) : (
                    <>{f.value}{f.suffix || ""}</>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {availableAnalystFields.length > 0 && (
        <div className="rounded-2xl bg-premium-bg border border-white/5 p-6">
          <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-black">Analyst Ratings</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {availableAnalystFields.map((f) => (
              <div key={f.key}>
                <div className="text-[10px] text-slate-500 mb-1">{f.label}</div>
                <div className="text-sm font-bold text-white">{f.fmt === "currency" ? formatValue(f.value, "currency") : f.value}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {newsItems.length > 0 && (
        <div className="rounded-2xl bg-premium-bg border border-white/5 p-6">
          <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-black">Latest News</div>
          <div className="space-y-3">
            {newsItems.filter((n) => n.title || n.snippet).map((news, i) => {
              const content = (
                <>
                  <span className="text-cyan-500 mt-1 shrink-0 text-xs group-hover:text-cyan-400">↗</span>
                  <div className="min-w-0 flex-1">
                    <div className="text-[13px] text-slate-200 font-medium leading-snug group-hover:text-white">
                      {news.title || news.snippet?.slice(0, 80)}
                    </div>
                    {news.snippet && news.title && news.snippet !== news.title && (
                      <p className="text-[12px] text-slate-500 mt-1.5 leading-relaxed line-clamp-2">{news.snippet}</p>
                    )}
                    <div className="flex flex-wrap gap-2 mt-1.5">
                      {news.source && <span className="text-[10px] text-slate-500">{news.source}</span>}
                      {news.date && <span className="text-[10px] text-slate-600">{news.date}</span>}
                    </div>
                  </div>
                </>
              );
              if (news.url) {
                return (
                  <a
                    key={i}
                    href={news.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full text-left flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5 hover:border-cyan-500/30 hover:bg-cyan-500/5 transition-all group"
                  >
                    {content}
                  </a>
                );
              }
              return (
                <div
                  key={i}
                  className="w-full flex items-start gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5"
                >
                  <span className="text-slate-600 mt-1 shrink-0 text-xs">●</span>
                  <div className="min-w-0 flex-1">
                    <div className="text-[13px] text-slate-200 font-medium leading-snug">{news.title || news.snippet}</div>
                    {news.snippet && news.title && <p className="text-[12px] text-slate-500 mt-1.5 leading-relaxed">{news.snippet}</p>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {hasValue(data.report) && (
        <ReportBlock title="Detailed Investment Case" report={data.report} />
      )}
    </div>
  );
}

function ResumeResults({ data }) {
  if (!data) return null;
  const atsScore = data?.atsScore ?? 0;
  const skillMatch = data?.skillMatch ?? 0;
  const atsLabel = atsScore >= 75 ? "STRONG" : atsScore >= 55 ? "FAIR" : "NEEDS WORK";
  const skillLabel = skillMatch >= 65 ? "HIGH" : skillMatch >= 35 ? "MODERATE" : "LOW";
  const breakdown = data?.scoreBreakdown || {};
  const keywordPct = data?.keywordMatchPct;

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <motion.div 
          whileHover={{ y: -4 }}
          className="p-6 rounded-2xl bg-gradient-to-br from-violet-600/10 via-purple-600/5 to-transparent border border-violet-500/20 shadow-lg shadow-violet-500/5"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="text-[10px] text-violet-400 uppercase tracking-widest font-black">ATS Score</div>
            <div className="text-[10px] font-bold text-violet-400 px-2 py-0.5 rounded bg-violet-500/10 border border-violet-500/20">{atsLabel}</div>
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-5xl font-black text-white tracking-tighter">{atsScore}</div>
            <div className="text-slate-500 text-lg font-bold">/ 100</div>
          </div>
          {keywordPct != null && (
            <div className="text-[11px] text-slate-500 mt-2">Role keyword match: {keywordPct}%</div>
          )}
          <div className="w-full h-2.5 rounded-full bg-black/40 mt-4 overflow-hidden border border-white/5 p-[1px]">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${atsScore}%` }}
              transition={{ duration: 1, ease: "circOut" }}
              className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 shadow-[0_0_12px_rgba(139,92,246,0.5)]"
            />
          </div>
          {Object.keys(breakdown).length > 0 && (
            <div className="grid grid-cols-2 gap-2 mt-4">
              {Object.entries(breakdown).map(([k, v]) => (
                <div key={k} className="text-[10px] text-slate-500">
                  <span className="capitalize">{k}</span>: <span className="text-violet-300 font-semibold">{v}</span>
                </div>
              ))}
            </div>
          )}
        </motion.div>
        
        <motion.div 
          whileHover={{ y: -4 }}
          className="p-6 rounded-2xl bg-gradient-to-br from-cyan-600/10 via-blue-600/5 to-transparent border border-cyan-500/20 shadow-lg shadow-cyan-500/5"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="text-[10px] text-cyan-400 uppercase tracking-widest font-black">Target Role Alignment</div>
            <div className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
              skillLabel === "HIGH" ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" :
              skillLabel === "MODERATE" ? "text-amber-400 bg-amber-500/10 border-amber-500/20" :
              "text-rose-400 bg-rose-500/10 border-rose-500/20"
            }`}>{skillLabel}</div>
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-5xl font-black text-white tracking-tighter">{skillMatch}</div>
            <div className="text-slate-500 text-lg font-bold">%</div>
          </div>
          {data?.wordCount && (
            <div className="text-[11px] text-slate-500 mt-2">{data.wordCount} words analyzed</div>
          )}
          <div className="w-full h-2.5 rounded-full bg-black/40 mt-4 overflow-hidden border border-white/5 p-[1px]">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${skillMatch}%` }}
              transition={{ duration: 1, ease: "circOut" }}
              className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 shadow-[0_0_12px_rgba(6,182,212,0.5)]"
            />
          </div>
        </motion.div>
      </div>

      <div className="grid md:grid-cols-2 gap-5">
        <ResultList title="Top Candidate Strengths" items={data?.strengths || []} tone="text-emerald-400" marker="★" />
        <ResultList title="Critical Skill Gaps" items={data?.missingSkills || []} tone="text-rose-400" marker="⚠" />
      </div>

      <AtsBreakdownTable rows={data?.atsBreakdown} />
      <BulletRewriteCards items={data?.bulletRewrites} role={data?.role} />

      <ReportBlock title="Career Coach Report" report={data?.recruiterFeedback || data?.report} />

      {data?.suggestions?.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-6 rounded-2xl bg-gradient-to-br from-amber-600/5 via-orange-600/5 to-transparent border border-amber-500/20 shadow-lg"
        >
          <div className="flex items-center gap-3 mb-5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center text-sm shadow-lg">⚡</div>
            <div>
              <div className="text-[10px] text-amber-400 uppercase tracking-widest font-black">Profile Improvement Plan</div>
              <div className="text-[11px] text-slate-500">Actionable steps to boost your ATS & skill match scores</div>
            </div>
          </div>
          <div className="space-y-3">
            {data.suggestions.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-start gap-3 p-3.5 rounded-xl bg-white/[0.03] border border-white/5 hover:border-amber-500/30 transition-all"
              >
                <span className="w-6 h-6 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center text-xs font-black shrink-0 mt-0.5">{i + 1}</span>
                <span className="text-[13px] text-slate-300 leading-relaxed">{item}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}

function ResultList({ title, items = [], tone, marker }) {
  if (!items.length) return null;
  return (
    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors h-full flex flex-col">
      <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-black">{title}</div>
      <div className="space-y-4 flex-1">
        {items.map((item, index) => (
          <div key={`${item}-${index}`} className="flex items-start gap-4">
            <span className={`mt-0.5 text-base leading-none shrink-0 ${tone}`}>{marker}</span>
            <span className="text-[13px] text-slate-300 leading-relaxed opacity-90 break-words">{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

const scoreColors = {
  Excellent: { stroke: "#22C55E", bg: "rgba(34,197,94,0.15)", text: "text-emerald-400", track: "stroke-emerald-500/10" },
  Good: { stroke: "#3B82F6", bg: "rgba(59,130,246,0.15)", text: "text-blue-400", track: "stroke-blue-500/10" },
  "Needs Work": { stroke: "#F97316", bg: "rgba(249,115,22,0.15)", text: "text-orange-400", track: "stroke-orange-500/10" },
  Poor: { stroke: "#EF4444", bg: "rgba(239,68,68,0.15)", text: "text-red-400", track: "stroke-red-500/10" },
};

function ScoreRing({ label, score, scoreLabel, size = 140 }) {
  const colors = scoreColors[scoreLabel] || scoreColors.Poor;
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="flex flex-col items-center gap-2"
    >
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
          <motion.circle
            cx={size / 2} cy={size / 2} r={radius} fill="none"
            stroke={colors.stroke} strokeWidth="8" strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.2, ease: "easeOut" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-black text-white">{score}</span>
          <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: colors.stroke }}>{scoreLabel}</span>
        </div>
      </div>
      <span className="text-[10px] text-slate-500 uppercase tracking-widest font-black text-center">{label}</span>
    </motion.div>
  );
}

function WebsiteAuditResults({ data, screenshot }) {
  const scores = data.scores || {};
  const issues = data.issues || [];
  const suggestions = data.suggestions || [];

  const scoreKeys = [
    { key: "on_page_seo", label: "On-Page SEO" },
    { key: "performance", label: "Performance" },
    { key: "accessibility", label: "Accessibility" },
    { key: "seo", label: "SEO" },
    { key: "best_practices", label: "Best Practices" },
  ];

  return (
    <div className="space-y-8">
      {screenshot && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl bg-premium-bg border border-white/5 p-6 overflow-hidden"
        >
          <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-4 font-black flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-gradient-to-r from-amber-400 to-orange-500" />
            Desktop Preview
          </div>
          <div className="relative w-full rounded-xl overflow-hidden border border-white/5 shadow-2xl" style={{ maxHeight: 400 }}>
            <motion.img
              src={screenshot}
              alt="Desktop preview"
              className="w-full h-auto object-top object-cover"
              initial={{ opacity: 0, scale: 1.05 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              style={{ maxHeight: 400 }}
            />
            <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-premium-bg to-transparent pointer-events-none" />
          </div>
        </motion.div>
      )}

      <div className="rounded-2xl bg-premium-bg border border-white/5 p-6">
        <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-7 font-black flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-gradient-to-r from-amber-400 to-orange-500" />
          Audit Scores
          {data.url && <span className="text-[10px] text-slate-600 font-mono ml-auto truncate max-w-[300px]">{data.url}</span>}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-6 justify-items-center">
          {scoreKeys.map(({ key, label: ringLabel }) => {
            const s = scores[key];
            if (!s) return null;
            return <ScoreRing key={key} label={ringLabel} score={s.score} scoreLabel={s.label} />;
          })}
        </div>
      </div>

      {issues.length > 0 && (
        <div className="rounded-2xl bg-premium-bg border border-rose-500/10 p-6">
          <div className="text-[10px] text-rose-400 uppercase tracking-widest mb-5 font-black flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            Issues Found ({issues.length})
          </div>
          <div className="space-y-3">
            {issues.map((issue, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-start gap-3 p-3 rounded-xl bg-rose-500/5 border border-rose-500/10"
              >
                <span className="text-rose-400 mt-0.5 shrink-0 text-sm">⚠</span>
                <span className="text-[13px] text-slate-300 leading-relaxed">{issue}</span>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {suggestions.length > 0 && (
        <div className="rounded-2xl bg-premium-bg border border-emerald-500/10 p-6">
          <div className="text-[10px] text-emerald-400 uppercase tracking-widest mb-5 font-black flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            Suggestions ({suggestions.length})
          </div>
          <div className="space-y-3">
            {suggestions.map((suggestion, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className="flex items-start gap-3 p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/10"
              >
                <span className="text-emerald-400 mt-0.5 shrink-0 text-sm">✦</span>
                <span className="text-[13px] text-slate-300 leading-relaxed">{suggestion}</span>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ResultsDisplay({ type, data, screenshot }) {
  if (!data) return null;
  if (type === "stock") return <StockResults data={data} />;
  if (type === "resume") return <ResumeResults data={data} />;
  if (type === "website_audit") return <WebsiteAuditResults data={data} screenshot={screenshot} />;
  return null;
}

function IdleMissionControl({ logs, providerStatus, backendConnected, onOpenSettings }) {
  return (
    <div className="h-full grid lg:grid-cols-[1fr_280px] gap-6">
      <div className="rounded-2xl bg-black/60 border border-white/5 p-6 flex flex-col shadow-2xl">
        <div className="flex items-center justify-between mb-4">
          <div className="text-[10px] text-slate-500 uppercase tracking-widest font-black">System Ready</div>
          <div className="flex gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500/40" />
          </div>
        </div>
        <div className="flex-1 min-h-[300px] overflow-y-auto custom-scrollbar">
          {logs.map((log, index) => (
            <LogLine key={`${log}-${index}`} text={log} isLatest={index === logs.length - 1} />
          ))}
          <LogLine text="Select a scenario to initialize the agentic pipeline." isLatest />
        </div>
      </div>
      <div className="space-y-4">
        <div className="rounded-2xl bg-premium-surface border border-white/5 p-5 shadow-xl">
          <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-4 font-black">Connectivity</div>
          <div className="flex items-center gap-3">
            <span className={`inline-block w-2.5 h-2.5 rounded-full ${backendConnected ? "bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]" : "bg-rose-400"}`} />
            <div className="text-white font-bold text-sm tracking-tight">{backendConnected ? "FastAPI Online" : "Service Offline"}</div>
          </div>
          <div className="text-[10px] font-mono text-slate-500 mt-2 truncate">{providerStatus}</div>
          <button
            type="button"
            onClick={onOpenSettings}
            className="mt-5 w-full py-2.5 rounded-xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-400 text-xs font-black hover:bg-cyan-400/15 transition-all uppercase tracking-widest"
          >
            Manage Keys
          </button>
        </div>
        <div className="rounded-2xl bg-premium-surface border border-white/5 p-5 shadow-xl overflow-hidden">
          <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-4 font-black">Active Nodes</div>
          <div className="space-y-3">
            {Object.values(AGENT_CONFIGS).map((config) => (
              <div key={config.id} className="flex items-center justify-between">
                <span className="text-xs text-slate-400 font-medium">{config.title.split(' ')[0]} Analyser</span>
                <span className={`h-1.5 w-1.5 rounded-full ${backendConnected ? "bg-emerald-400" : "bg-slate-700"}`} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function RightPanel({
  agentId,
  status,
  workflow,
  logs,
  progress,
  results,
  screenshot,
  providerStatus,
  backendConnected,
  lastError,
  creditAlert,
  onDismissCreditAlert,
  onOpenSettings,
}) {
  const config = agentId ? AGENT_CONFIGS[agentId] : null;
  const isRunning = status === "running";
  const isCompleted = status === "completed";
  const isFailed = status === "failed";

  if (!config) {
    return <IdleMissionControl logs={logs} providerStatus={providerStatus} backendConnected={backendConnected} onOpenSettings={onOpenSettings} />;
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-6 border-b border-white/5">
        <div className="flex items-center gap-4">
          <div className={`w-10 h-10 rounded-2xl bg-gradient-to-br ${config.gradient} flex items-center justify-center text-xl shadow-lg shadow-black/20`}>
            {config.id === "stock" ? "📈" : config.id === "website_audit" ? "🌐" : "📄"}
          </div>
          <div>
            <h3 className="text-white font-black text-base tracking-tight">{config.title}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`w-1.5 h-1.5 rounded-full ${isRunning ? "bg-cyan-400 animate-pulse shadow-[0_0_8px_rgba(34,211,238,1)]" : isCompleted ? "bg-emerald-400" : isFailed ? "bg-rose-400" : "bg-slate-600"}`} />
              <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest">{status}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onOpenSettings}
            className={`text-[10px] font-black rounded-xl px-4 py-2 border transition-all tracking-widest uppercase ${
              providerStatus.includes("Connected")
                ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-400 hover:bg-emerald-500/10"
                : "border-amber-500/20 bg-amber-500/5 text-amber-400 hover:bg-amber-500/10"
            }`}
          >
            {providerStatus.includes("Connected") ? "AI Online" : "Auth Required"}
          </button>
        </div>
      </div>

      <div className="mb-8">
        <div className="flex items-center justify-between mb-2.5 px-1">
          <span className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Pipeline Orchestration</span>
          <span className="text-[11px] text-white font-black font-mono">{progress}%</span>
        </div>
        <ProgressBar progress={progress} />
      </div>

      {creditAlert && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 rounded-2xl border border-amber-500/20 bg-amber-500/5 p-4 flex items-start gap-3"
        >
          <span className="text-amber-400 text-lg leading-none mt-0.5">⚡</span>
          <div className="flex-1">
            <div className="text-[10px] text-amber-400 uppercase tracking-widest font-bold mb-1">API Credit Limit</div>
            <p className="text-xs text-amber-200/70 leading-relaxed">{creditAlert}</p>
          </div>
          <button
            onClick={onDismissCreditAlert}
            className="text-slate-600 hover:text-slate-400 text-sm leading-none"
          >
            ✕
          </button>
        </motion.div>
      )}

      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-3 pb-8">
        {!results ? (
          <div className="grid lg:grid-cols-[1fr_240px] gap-8 h-full">
            <div className="space-y-8 flex flex-col h-full">
              <div className="flex-1 rounded-2xl bg-premium-bg border border-white/5 p-6 shadow-2xl flex flex-col min-h-[340px]">
                <div className="flex items-center justify-between mb-4">
                  <div className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Live Telemetry</div>
                  <div className="flex gap-1">
                    <span className={`w-1 h-1 rounded-full ${isRunning ? "bg-cyan-400 animate-ping" : "bg-slate-700"}`} />
                    <span className="text-[9px] text-slate-600 font-mono">{isRunning ? "POLLING" : "IDLE"}</span>
                  </div>
                </div>
                <div className="flex-1 space-y-1 overflow-y-auto custom-scrollbar pr-2">
                  {logs.map((log, index) => (
                    <LogLine key={`${log}-${index}`} text={log} isLatest={index === logs.length - 1 && isRunning} />
                  ))}
                </div>
              </div>
              
              {!isRunning && !isCompleted && !isFailed && (
                <div className="rounded-3xl bg-white/[0.02] border border-white/5 p-10 flex flex-col items-center justify-center text-center shadow-inner">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 flex items-center justify-center text-3xl mb-5 border border-white/5 shadow-2xl">
                    ⚡
                  </div>
                  <h4 className="text-white font-bold mb-2">Initialize Analysis</h4>
                  <p className="text-xs text-slate-500 max-w-xs leading-relaxed">
                    Provide the required inputs to start the multi-agent workflow. The system will coordinate and stream results here.
                  </p>
                </div>
              )}
            </div>

            <div className="space-y-5 h-full">
              <div className="text-[10px] text-slate-500 uppercase tracking-widest font-black mb-1">
                Task Graph
              </div>
              <div className="space-y-3">
                {workflow.map((step, index) => (
                  <WorkflowStep key={step.id} step={step} status={step.status} index={index} />
                ))}
              </div>
              
              {isRunning && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="mt-8 p-5 rounded-2xl border border-indigo-500/20 bg-indigo-500/5"
                >
                  <div className="text-[10px] text-indigo-300 font-black uppercase tracking-widest mb-2">Agent Sync</div>
                  <p className="text-[11px] text-slate-400 leading-relaxed italic opacity-80">
                    Nodes are synchronized. Exchanging data packets between Career Coach and ATS modules...
                  </p>
                </motion.div>
              )}
            </div>
          </div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            <div className="flex items-center gap-4">
              <div className="h-px flex-1 bg-white/5" />
              <div className="text-[10px] text-emerald-400 uppercase tracking-[0.2em] font-black whitespace-nowrap px-4 py-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/5 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Analytical Report Ready
              </div>
              <div className="h-px flex-1 bg-white/5" />
            </div>
            
            <ResultsDisplay type={config.resultType} data={results} screenshot={screenshot} />
          </motion.div>
        )}
      </div>
    </div>
  );
}
