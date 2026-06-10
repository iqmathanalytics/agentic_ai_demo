import { motion } from "framer-motion";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from "recharts";
import { AGENT_CONFIGS, generateMockResults } from "./agentsData";

const statusIcons = {
  idle: "○",
  running: "◉",
  completed: "✓",
  failed: "✕",
};

const statusColors = {
  idle: "text-slate-500",
  running: "text-blue-400",
  completed: "text-emerald-400",
  failed: "text-red-400",
};

const statusBg = {
  idle: "bg-slate-500/20 border-slate-500/30",
  running: "bg-blue-500/20 border-blue-500/30",
  completed: "bg-emerald-500/20 border-emerald-500/30",
  failed: "bg-red-500/20 border-red-500/30",
};

function LogLine({ text, isLatest }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className={`flex items-start gap-2 py-1 text-xs font-mono ${
        isLatest ? "text-cyan-300" : "text-slate-500"
      }`}
    >
      <span className="text-slate-600 shrink-0 select-none">{">"}</span>
      <span>{text}</span>
      {isLatest && (
        <span className="inline-block w-1.5 h-4 bg-cyan-400/70 animate-pulse ml-0.5" />
      )}
    </motion.div>
  );
}

function WorkflowStep({ step, status, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className={`flex items-center gap-3 p-3 rounded-lg border transition-all duration-500 ${
        status === "running"
          ? "border-blue-500/40 bg-blue-500/10"
          : status === "completed"
            ? "border-emerald-500/30 bg-emerald-500/10"
            : status === "failed"
              ? "border-red-500/30 bg-red-500/10"
              : "border-white/5 bg-white/[0.03]"
      }`}
    >
      <div
        className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm ${
          statusBg[status]
        }`}
      >
        {status === "running" ? (
          <motion.span
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
            className="block"
          >
            {statusIcons.running}
          </motion.span>
        ) : (
          <span className={statusColors[status]}>{statusIcons[status]}</span>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className={`text-sm font-medium ${status === "idle" ? "text-slate-500" : "text-white"}`}>
          {step.icon} {step.name}
        </div>
      </div>
      {status === "running" && (
        <motion.div
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
          className="text-[10px] text-blue-400 font-mono"
        >
          processing...
        </motion.div>
      )}
    </motion.div>
  );
}

function ProgressBar({ progress }) {
  return (
    <div className="relative h-1.5 rounded-full bg-white/5 overflow-hidden">
      <motion.div
        className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-blue-500 via-indigo-500 to-cyan-500"
        initial={{ width: 0 }}
        animate={{ width: `${progress}%` }}
        transition={{ duration: 0.5, ease: "easeOut" }}
      />
    </div>
  );
}

function CustomTooltip({ active, payload }) {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#121826] border border-white/10 rounded-lg px-3 py-2 shadow-xl">
        <p className="text-white text-xs font-mono">{payload[0].payload.time}</p>
        <p className="text-cyan-400 text-xs font-mono">₹{payload[0].value.toFixed(2)}</p>
      </div>
    );
  }
  return null;
}

function StockResults({ data }) {
  if (!data) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <div className="rounded-xl bg-black/40 border border-white/5 p-4">
        <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-3">Price Trend</div>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={data.chartData}>
            <defs>
              <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#06B6D4" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#06B6D4" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#64748B" }} axisLine={false} tickLine={false} />
            <YAxis domain={["dataMin - 20", "dataMax + 20"]} tick={{ fontSize: 10, fill: "#64748B" }} axisLine={false} tickLine={false} tickFormatter={(v) => `₹${v}`} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="value" stroke="#06B6D4" strokeWidth={2} fill="url(#priceGradient)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Current Price</div>
          <div className="text-lg font-bold text-white mt-1">
            ₹{data.currentPrice.toFixed(2)}
          </div>
          <div className={`text-xs font-medium ${data.change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
            {data.change >= 0 ? "+" : ""}{data.change}%
          </div>
        </div>
        <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Recommendation</div>
          <div className="text-lg font-bold text-emerald-400 mt-1">{data.recommendation}</div>
          <div className="text-xs text-slate-400">Confidence: {data.confidence}%</div>
        </div>
        <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">RSI</div>
          <div className="text-lg font-bold text-white mt-1">{data.rsi}</div>
          <div className="text-xs text-slate-400">Neutral zone</div>
        </div>
        <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Sentiment</div>
          <div className={`text-lg font-bold mt-1 ${data.sentiment === "Positive" ? "text-emerald-400" : "text-amber-400"}`}>
            {data.sentiment}
          </div>
          <div className="text-xs text-slate-400">Risk: {data.risk}</div>
        </div>
      </div>

      <div className="rounded-xl bg-black/40 border border-white/5 p-4">
        <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-3">Signal Analysis</div>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart data={data.signalData}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="name" tick={{ fontSize: 8, fill: "#64748B" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 8, fill: "#64748B" }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Line type="monotone" dataKey="signals" stroke="#6366F1" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="trend" stroke="#3B82F6" strokeWidth={2} dot={false} strokeDasharray="4 4" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

function ResumeResults({ data }) {
  if (!data) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">ATS Score</div>
          <div className="text-2xl font-bold text-white mt-1">{data.atsScore}<span className="text-sm text-slate-400">/100</span></div>
          <div className="w-full h-1.5 rounded-full bg-white/5 mt-2 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${data.atsScore}%` }}
              className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-500"
              transition={{ duration: 1, delay: 0.3 }}
            />
          </div>
        </div>
        <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Skill Match</div>
          <div className="text-2xl font-bold text-white mt-1">{data.skillMatch}<span className="text-sm text-slate-400">%</span></div>
          <div className="w-full h-1.5 rounded-full bg-white/5 mt-2 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${data.skillMatch}%` }}
              className="h-full rounded-full bg-gradient-to-r from-amber-500 to-orange-500"
              transition={{ duration: 1, delay: 0.3 }}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Strengths</div>
          {data.strengths.map((s, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-emerald-400 mb-1.5">
              <span className="mt-0.5">+</span>
              <span>{s}</span>
            </div>
          ))}
        </div>
        <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Weaknesses</div>
          {data.weaknesses.map((w, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-red-400 mb-1.5">
              <span className="mt-0.5">-</span>
              <span>{w}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
        <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Missing Skills</div>
        <div className="flex flex-wrap gap-1.5">
          {data.missingSkills.map((s) => (
            <span key={s} className="px-2 py-1 rounded-md text-[10px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
              {s}
            </span>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function LinkedInResults({ data }) {
  if (!data) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Profile Score</div>
          <div className="text-2xl font-bold text-white mt-1">{data.profileScore}<span className="text-sm text-slate-400">/100</span></div>
          <div className="w-full h-1.5 rounded-full bg-white/5 mt-2 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${data.profileScore}%` }}
              className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500"
              transition={{ duration: 1, delay: 0.3 }}
            />
          </div>
        </div>
        <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Visibility Score</div>
          <div className="text-2xl font-bold text-white mt-1">{data.visibilityScore}<span className="text-sm text-slate-400">/100</span></div>
          <div className="w-full h-1.5 rounded-full bg-white/5 mt-2 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${data.visibilityScore}%` }}
              className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-blue-500"
              transition={{ duration: 1, delay: 0.3 }}
            />
          </div>
        </div>
      </div>

      <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
        <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Headline Suggestions</div>
        {data.headlineSuggestions.map((s, i) => (
          <div key={i} className="flex items-start gap-2 text-xs text-slate-300 mb-1.5">
            <span className="text-blue-400 mt-0.5">→</span>
            <span>{s}</span>
          </div>
        ))}
      </div>

      <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
        <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">Improvement Tips</div>
        {data.tips.map((t, i) => (
          <div key={i} className="flex items-start gap-2 text-xs text-slate-300 mb-1.5">
            <span className="text-emerald-400 mt-0.5">◆</span>
            <span>{t}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function ResultsDisplay({ type, data }) {
  if (!data) return null;
  switch (type) {
    case "stock":
      return <StockResults data={data} />;
    case "resume":
      return <ResumeResults data={data} />;
    case "linkedin":
      return <LinkedInResults data={data} />;
    default:
      return null;
  }
}

export default function RightPanel({ agentId, status, workflow, logs, progress, results }) {
  const config = agentId ? AGENT_CONFIGS[agentId] : null;
  const isRunning = status === "running";
  const isCompleted = status === "completed";

  if (!config) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4 opacity-30">🤖</div>
          <p className="text-slate-500 text-sm">Select an agent scenario to begin</p>
          <p className="text-slate-600 text-xs mt-1">Choose from the cards on the left</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-white/5">
        <div>
          <h3 className="text-white font-semibold text-sm">{config.title}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${
              status === "idle" ? "bg-slate-500" :
              status === "running" ? "bg-blue-400 animate-pulse" :
              status === "completed" ? "bg-emerald-400" : "bg-red-400"
            }`} />
            <span className="text-[10px] text-slate-500 font-mono uppercase">
              {status}
            </span>
          </div>
        </div>
        {(status === "idle" || status === "completed") && (
          <div className="text-[10px] text-slate-500 font-mono">
            {isCompleted ? "Ready for next run" : "Awaiting input"}
          </div>
        )}
      </div>

      {progress > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] text-slate-500 font-mono">Progress</span>
            <span className="text-[10px] text-slate-400 font-mono">{progress}%</span>
          </div>
          <ProgressBar progress={progress} />
        </div>
      )}

      <div className="flex-1 space-y-4 overflow-y-auto custom-scrollbar pr-1">
        {isRunning && workflow && (
          <div className="space-y-2">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-2">
              Agent Pipeline
            </div>
            {workflow.map((step, i) => (
              <WorkflowStep key={step.id} step={step} status={step.status} index={i} />
            ))}
          </div>
        )}

        {logs.length > 0 && (
          <div className="rounded-xl bg-black/40 border border-white/5 p-4">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-3">
              Execution Console
            </div>
            <div className="space-y-0.5 max-h-[200px] overflow-y-auto custom-scrollbar">
              {logs.map((log, i) => (
                <LogLine key={i} text={log} isLatest={i === logs.length - 1 && isRunning} />
              ))}
            </div>
          </div>
        )}

        {isCompleted && results && (
          <div>
            <div className="text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-3">
              Analysis Results
            </div>
            <ResultsDisplay type={config.resultType} data={results} />
          </div>
        )}
      </div>
    </div>
  );
}
