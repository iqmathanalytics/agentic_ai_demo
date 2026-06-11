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
    <div className="bg-[#0B0F19] border border-white/10 rounded-xl px-4 py-3 shadow-2xl backdrop-blur-md">
      <p className="text-slate-500 text-[10px] font-mono mb-1 uppercase tracking-tighter">{payload[0].payload.time}</p>
      <p className="text-cyan-400 text-sm font-bold font-mono">${Number(payload[0].value).toLocaleString()}</p>
    </div>
  );
}

function ReportBlock({ title, report }) {
  if (!report) return null;
  return (
    <div className="rounded-2xl bg-[#0B0F19] border border-white/5 p-6 shadow-inner">
      <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-bold flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-gradient-to-r from-cyan-400 to-blue-500" />
        {title}
      </div>
      <div className="prose prose-invert max-w-none">
        <div className="whitespace-pre-wrap text-[13px] text-slate-300 leading-relaxed font-sans opacity-90">{report}</div>
      </div>
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
    <div className="space-y-8">
      {hasChart && (
        <div className="rounded-2xl bg-white/[0.02] border border-white/5 p-6 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-6">
            <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Historical Performance</div>
            <div className="px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 text-[10px] font-bold border border-cyan-500/20">LIVE DATA</div>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={data.chartData}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#06B6D4" stopOpacity={0.4} />
                  <stop offset="100%" stopColor="#06B6D4" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
              <XAxis dataKey="time" tick={{ fontSize: 9, fill: "#475569" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 9, fill: "#475569" }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="value" stroke="#06B6D4" strokeWidth={2.5} fill="url(#priceGradient)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
        {[
          ["Current Price", data.currentPrice != null ? `$${data.currentPrice.toLocaleString()}` : "N/A", "text-white"],
          ["24h Change", data.change != null ? `${data.change}%` : "N/A", data.change >= 0 ? "text-emerald-400" : "text-rose-400"],
          ["SMA 20 Day", data.sma20 ?? "N/A", "text-slate-300"],
          ["SMA 50 Day", data.sma50 ?? "N/A", "text-slate-300"],
          ["Trading Volume", data.volume != null ? data.volume.toLocaleString() : "N/A", "text-slate-300"],
          ["Market Cap", formatMarketCap(data.marketCap), "text-slate-300"],
        ].map(([label, value, color]) => (
          <div key={label} className="p-5 rounded-2xl bg-[#121826] border border-white/5 transition-all hover:border-white/10 hover:shadow-xl">
            <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-2 font-bold">{label}</div>
            <div className={`text-xl font-black ${color}`}>{value}</div>
          </div>
        ))}
      </div>
      <ReportBlock title="Investment Thesis & Risks" report={data.report} />
    </div>
  );
}

function ResumeResults({ data }) {
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <motion.div 
          whileHover={{ y: -4 }}
          className="p-6 rounded-2xl bg-gradient-to-br from-violet-600/10 via-purple-600/5 to-transparent border border-violet-500/20 shadow-lg shadow-violet-500/5"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="text-[10px] text-violet-400 uppercase tracking-widest font-black">ATS Match Potential</div>
            <div className="text-[10px] font-bold text-violet-400 px-2 py-0.5 rounded bg-violet-500/10 border border-violet-500/20">PASSED</div>
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-5xl font-black text-white tracking-tighter">{data.atsScore}</div>
            <div className="text-slate-500 text-lg font-bold">/ 100</div>
          </div>
          <div className="w-full h-2.5 rounded-full bg-black/40 mt-6 overflow-hidden border border-white/5 p-[1px]">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${data.atsScore}%` }}
              transition={{ duration: 1, ease: "circOut" }}
              className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500 shadow-[0_0_12px_rgba(139,92,246,0.5)]"
            />
          </div>
        </motion.div>
        
        <motion.div 
          whileHover={{ y: -4 }}
          className="p-6 rounded-2xl bg-gradient-to-br from-cyan-600/10 via-blue-600/5 to-transparent border border-cyan-500/20 shadow-lg shadow-cyan-500/5"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="text-[10px] text-cyan-400 uppercase tracking-widest font-black">Target Role Alignment</div>
            <div className="text-[10px] font-bold text-cyan-400 px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20">HIGH</div>
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-5xl font-black text-white tracking-tighter">{data.skillMatch}</div>
            <div className="text-slate-500 text-lg font-bold">%</div>
          </div>
          <div className="w-full h-2.5 rounded-full bg-black/40 mt-6 overflow-hidden border border-white/5 p-[1px]">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${data.skillMatch}%` }}
              transition={{ duration: 1, ease: "circOut" }}
              className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 shadow-[0_0_12px_rgba(6,182,212,0.5)]"
            />
          </div>
        </motion.div>
      </div>

      <div className="grid md:grid-cols-2 gap-5">
        <ResultList title="Top Candidate Strengths" items={data.strengths} tone="text-emerald-400" marker="★" />
        <ResultList title="Critical Skill Gaps" items={data.weaknesses} tone="text-rose-400" marker="⚠" />
      </div>

      <div className="p-6 rounded-2xl bg-[#0F172A] border border-white/5">
        <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-black">Missing Technical Keywords</div>
        <div className="flex flex-wrap gap-2.5">
          {data.missingSkills.map((item) => (
            <span key={item} className="px-3.5 py-2 rounded-xl text-[11px] font-bold bg-white/5 text-slate-300 border border-white/10 hover:border-cyan-500/50 hover:text-cyan-400 transition-all cursor-default">
              {item}
            </span>
          ))}
          {data.missingSkills.length === 0 && <span className="text-xs text-slate-600 italic">No missing skills detected based on the target profile.</span>}
        </div>
      </div>
      
      <ResultList title="Personalized Career Roadmap" items={data.suggestions} tone="text-cyan-400" marker="➜" />

      <ReportBlock title="Executive Recruiter Insight & Feedback" report={data.recruiterFeedback || data.report} />
    </div>
  );
}

function ResultList({ title, items = [], tone, marker }) {
  if (!items.length) return null;
  return (
    <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/5 hover:border-white/10 transition-colors">
      <div className="text-[10px] text-slate-500 uppercase tracking-widest mb-5 font-black">{title}</div>
      <div className="space-y-4">
        {items.map((item, index) => (
          <div key={`${item}-${index}`} className="flex items-start gap-4">
            <span className={`mt-0.5 text-base leading-none ${tone}`}>{marker}</span>
            <span className="text-[13px] text-slate-300 leading-relaxed opacity-90">{item}</span>
          </div>
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
        <div className="rounded-2xl bg-[#121826] border border-white/5 p-5 shadow-xl">
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
        <div className="rounded-2xl bg-[#121826] border border-white/5 p-5 shadow-xl overflow-hidden">
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
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-6 border-b border-white/5">
        <div className="flex items-center gap-4">
          <div className={`w-10 h-10 rounded-2xl bg-gradient-to-br ${config.gradient} flex items-center justify-center text-xl shadow-lg shadow-black/20`}>
            {config.id === 'stock' ? '📈' : '📄'}
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

      {lastError && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-8 rounded-2xl border border-rose-500/20 bg-rose-500/5 p-5 text-xs text-rose-300 flex items-start gap-3"
        >
          <span className="text-lg">🚨</span>
          <div>
            <div className="font-bold mb-1 uppercase tracking-wider text-[10px]">Execution Interrupted</div>
            {lastError}
          </div>
        </motion.div>
      )}

      <div className="flex-1 grid lg:grid-cols-[1fr_240px] gap-8 min-h-0">
        <div className="space-y-8 overflow-y-auto custom-scrollbar pr-3 pb-10">
          {!results && (
            <div className="rounded-2xl bg-[#0B0F19] border border-white/5 p-6 shadow-2xl">
              <div className="flex items-center justify-between mb-4">
                <div className="text-[10px] text-slate-500 uppercase tracking-widest font-black">Live Telemetry</div>
                <div className="flex gap-1">
                  <span className={`w-1 h-1 rounded-full ${isRunning ? "bg-cyan-400 animate-ping" : "bg-slate-700"}`} />
                  <span className="text-[9px] text-slate-600 font-mono">{isRunning ? "POLLING" : "IDLE"}</span>
                </div>
              </div>
              <div className="space-y-1 max-h-[340px] overflow-y-auto custom-scrollbar">
                {logs.map((log, index) => (
                  <LogLine key={`${log}-${index}`} text={log} isLatest={index === logs.length - 1 && isRunning} />
                ))}
              </div>
            </div>
          )}

          {results && (
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-8"
            >
              <div className="flex items-center gap-4">
                <div className="h-px flex-1 bg-white/5" />
                <div className="text-[10px] text-emerald-400 uppercase tracking-[0.2em] font-black whitespace-nowrap px-4 py-1.5 rounded-full border border-emerald-500/20 bg-emerald-500/5">
                  Analytical Report Ready
                </div>
                <div className="h-px flex-1 bg-white/5" />
              </div>
              <ResultsDisplay type={config.resultType} data={results} />
            </motion.div>
          )}

          {!results && !isRunning && !isCompleted && !isFailed && (
            <div className="rounded-3xl bg-white/[0.02] border border-white/5 p-10 flex flex-col items-center justify-center text-center shadow-inner">
              <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-cyan-500/20 to-blue-500/20 flex items-center justify-center text-4xl mb-6 border border-white/5 shadow-2xl">
                ⚡
              </div>
              <h4 className="text-white font-bold mb-2">Initialize Analysis</h4>
              <p className="text-xs text-slate-500 max-w-xs leading-relaxed">
                Provide the required inputs to start the multi-agent workflow. The system will coordinate and stream results here.
              </p>
            </div>
          )}
        </div>

        <div className="space-y-5 overflow-y-auto custom-scrollbar pr-1 pb-10">
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
    </div>
  );
}
