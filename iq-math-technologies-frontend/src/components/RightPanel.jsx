import { motion } from "framer-motion";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
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
      className={`relative p-3 rounded-lg border transition-all duration-500 ${statusBg[status] || statusBg.idle}`}
    >
      {index > 0 && <div className="absolute -top-2 left-6 h-2 w-px bg-white/10" />}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg border border-white/10 bg-black/30 flex items-center justify-center">
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
          <div className={`text-sm font-medium ${status === "idle" ? "text-slate-500" : "text-white"}`}>
            {step.name}
          </div>
          <div className="text-[10px] uppercase tracking-wider text-slate-600 mt-0.5">
            {status === "running" ? "executing" : status}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function ProgressBar({ progress }) {
  return (
    <div className="relative h-1.5 rounded-full bg-white/5 overflow-hidden">
      <motion.div
        className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-cyan-500 via-blue-500 to-emerald-400"
        initial={{ width: 0 }}
        animate={{ width: `${progress}%` }}
        transition={{ duration: 0.35, ease: "easeOut" }}
      />
    </div>
  );
}

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#121826] border border-white/10 rounded-lg px-3 py-2 shadow-xl">
      <p className="text-white text-xs font-mono">{payload[0].payload.time}</p>
      <p className="text-cyan-400 text-xs font-mono">{Number(payload[0].value).toFixed(2)}</p>
    </div>
  );
}

function ReportBlock({ title, report }) {
  if (!report) return null;
  return (
    <div className="rounded-xl bg-black/40 border border-white/5 p-4">
      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-3">{title}</div>
      <div className="whitespace-pre-wrap text-sm text-slate-300 leading-relaxed">{report}</div>
    </div>
  );
}

function formatMarketCap(mc) {
  if (mc == null) return "Unavailable";
  if (mc >= 1e12) return `$${(mc / 1e12).toFixed(2)}T`;
  if (mc >= 1e9) return `$${(mc / 1e9).toFixed(2)}B`;
  if (mc >= 1e6) return `$${(mc / 1e6).toFixed(2)}M`;
  return `$${mc.toLocaleString()}`;
}

function StockResults({ data }) {
  const hasChart = data?.chartData?.length > 0;
  return (
    <div className="space-y-4">
      {hasChart && (
        <div className="rounded-xl bg-black/40 border border-white/5 p-4">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-3">Market Price Trend</div>
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
              <YAxis tick={{ fontSize: 10, fill: "#64748B" }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="value" stroke="#06B6D4" strokeWidth={2} fill="url(#priceGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid sm:grid-cols-2 gap-3">
        {[
          ["Current Price", data.currentPrice != null ? `$${data.currentPrice}` : "Unavailable"],
          ["Change", data.change != null ? `${data.change}%` : "Unavailable"],
          ["SMA 20", data.sma20 ?? "Unavailable"],
          ["SMA 50", data.sma50 ?? "Unavailable"],
          ["Volume", data.volume != null ? data.volume.toLocaleString() : "Unavailable"],
          ["Market Cap", formatMarketCap(data.marketCap)],
        ].map(([label, value]) => (
          <div key={label} className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</div>
            <div className="text-lg font-bold text-white mt-1">{value}</div>
          </div>
        ))}
      </div>
      <ReportBlock title="Investment Report" report={data.report} />
    </div>
  );
}

function ResumeResults({ data }) {
  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 gap-3">
        {[
          ["ATS Score", `${data.atsScore}/100`, data.atsScore],
          ["Skill Match", `${data.skillMatch}%`, data.skillMatch],
        ].map(([label, value, pct]) => (
          <div key={label} className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</div>
            <div className="text-2xl font-bold text-white mt-1">{value}</div>
            <div className="w-full h-1.5 rounded-full bg-white/5 mt-2 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                className="h-full rounded-full bg-gradient-to-r from-violet-500 to-cyan-500"
              />
            </div>
          </div>
        ))}
      </div>
      <ResultList title="Strengths" items={data.strengths} tone="text-emerald-400" marker="+" />
      <ResultList title="Weaknesses" items={data.weaknesses} tone="text-red-300" marker="-" />
      <TagList title="Missing Skills" items={data.missingSkills} />
      <ResultList title="Improvement Suggestions" items={data.suggestions} tone="text-slate-300" marker="→" />
      <ReportBlock title="Recruiter Feedback" report={data.recruiterFeedback || data.report} />
    </div>
  );
}

function ResultList({ title, items = [], tone, marker }) {
  if (!items.length) return null;
  return (
    <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">{title}</div>
      {items.map((item, index) => (
        <div key={`${item}-${index}`} className={`flex items-start gap-2 text-xs mb-1.5 ${tone}`}>
          <span className="mt-0.5">{marker}</span>
          <span className="text-slate-300">{item}</span>
        </div>
      ))}
    </div>
  );
}

function TagList({ title, items = [] }) {
  if (!items.length) return null;
  return (
    <div className="p-3 rounded-lg bg-white/[0.03] border border-white/5">
      <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">{title}</div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span key={item} className="px-2 py-1 rounded-md text-[10px] font-medium bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

function ResultsDisplay({ type, data }) {
  if (!data) return null;
  if (type === "stock") return <StockResults data={data} />;
  if (type === "resume") return <ResumeResults data={data} />;
  return null;
}

function IdleMissionControl({ logs, providerStatus, backendConnected, onOpenSettings }) {
  return (
    <div className="h-full grid lg:grid-cols-[1fr_280px] gap-4">
      <div className="rounded-xl bg-black/40 border border-white/5 p-4 flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Live Execution Console</div>
          <span className="text-[10px] text-cyan-300 font-mono">standby</span>
        </div>
        <div className="flex-1 min-h-[260px] overflow-y-auto custom-scrollbar">
          {logs.map((log, index) => (
            <LogLine key={`${log}-${index}`} text={log} isLatest={index === logs.length - 1} />
          ))}
          <LogLine text="Waiting for an agent card selection..." isLatest />
        </div>
      </div>
      <div className="space-y-3">
        <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider">Agent Status Bar</div>
          <div className="flex items-center gap-2 mt-2">
            <span className={`inline-block w-2 h-2 rounded-full ${backendConnected ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
            <div className="text-white font-semibold text-sm">{backendConnected ? "Backend Connected" : "Backend Disconnected"}</div>
          </div>
          <div className="text-xs text-slate-400 mt-1">{providerStatus}</div>
          <button
            type="button"
            onClick={onOpenSettings}
            className="mt-4 w-full py-2 rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-cyan-300 text-xs font-semibold hover:bg-cyan-400/15"
          >
            AI Providers
          </button>
        </div>
        <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-3">Available Pipelines</div>
          {Object.values(AGENT_CONFIGS).map((config) => (
            <div key={config.id} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
              <span className="text-xs text-slate-300">{config.title}</span>
              <span className={`h-1.5 w-1.5 rounded-full ${backendConnected ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`} />
            </div>
          ))}
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
  providerStatus,
  backendConnected,
  lastError,
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
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4 pb-4 border-b border-white/5">
        <div>
          <h3 className="text-white font-semibold text-sm">{config.title}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span
              className={`inline-block w-1.5 h-1.5 rounded-full ${
                status === "running"
                  ? "bg-cyan-300 animate-pulse"
                  : status === "completed"
                    ? "bg-emerald-400"
                    : status === "failed"
                      ? "bg-red-400"
                      : "bg-slate-500"
              }`}
            />
            <span className="text-[10px] text-slate-500 font-mono uppercase">{status}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className={`inline-block w-1.5 h-1.5 rounded-full ${backendConnected ? "bg-emerald-400" : "bg-red-400"}`} />
            <span className="text-[10px] text-slate-500 font-mono">{backendConnected ? "BE Online" : "BE Offline"}</span>
          </div>
          <button
            type="button"
            onClick={onOpenSettings}
            className={`text-[10px] font-semibold rounded-lg px-2.5 py-1.5 border ${
              providerStatus.includes("Connected")
                ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                : "border-amber-500/20 bg-amber-500/10 text-amber-300"
            }`}
          >
            {providerStatus.includes("Connected") ? "● AI Connected" : "● API Key Required"}
          </button>
        </div>
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-[10px] text-slate-500 font-mono">Progress</span>
          <span className="text-[10px] text-slate-400 font-mono">{progress}%</span>
        </div>
        <ProgressBar progress={progress} />
      </div>

      {lastError && (
        <div className="mb-4 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-200">
          {lastError}
        </div>
      )}

      <div className="flex-1 grid xl:grid-cols-[1fr_300px] gap-4 min-h-0">
        <div className="space-y-4 overflow-y-auto custom-scrollbar pr-1">
          <div className="rounded-xl bg-black/40 border border-white/5 p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
                Live Execution Console
              </div>
              <span className="text-[10px] text-cyan-300 font-mono">
                {isRunning ? "streaming" : isCompleted ? "complete" : isFailed ? "failed" : "ready"}
              </span>
            </div>
            <div className="space-y-0.5 max-h-[260px] overflow-y-auto custom-scrollbar">
              {logs.map((log, index) => (
                <LogLine key={`${log}-${index}`} text={log} isLatest={index === logs.length - 1 && isRunning} />
              ))}
            </div>
          </div>

          {results ? (
            <div>
              <div className="text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-3">
                Final Results
              </div>
              <ResultsDisplay type={config.resultType} data={results} />
            </div>
          ) : (
            <div className="rounded-xl bg-white/[0.03] border border-white/5 p-4 min-h-[180px]">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-3">Final Results</div>
              <div className="text-sm text-slate-400">
                {isRunning
                  ? "The final report will appear here as soon as the last agent completes."
                  : isFailed
                    ? "Agent execution failed. Check the error message above."
                    : "Submit the agent input form to start live execution."}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-3 overflow-y-auto custom-scrollbar pr-1">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
            Agent Pipeline
          </div>
          {workflow.map((step, index) => (
            <WorkflowStep key={step.id} step={step} status={step.status} index={index} />
          ))}
        </div>
      </div>
    </div>
  );
}
