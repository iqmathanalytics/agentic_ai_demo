import { motion } from "framer-motion";
import { AGENT_CONFIGS } from "./agentsData";

const statusColors = {
  Live: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  Beta: "bg-amber-500/20 text-amber-400 border-amber-500/30",
};

function AgentCard({ config, isSelected, onSelect, index }) {
  return (
    <motion.button
      initial={{ opacity: 0, x: -30 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5, ease: "easeOut" }}
      onClick={() => onSelect(config.id)}
      className={`relative w-full text-left p-5 rounded-xl border transition-all duration-500 cursor-pointer ${
        isSelected
          ? "border-blue-500/60 bg-blue-500/10 shadow-[0_0_30px_-5px_rgba(59,130,246,0.3)]"
          : "border-white/5 bg-white/[0.03] hover:bg-white/[0.06] hover:border-white/20"
      }`}
    >
      {isSelected && (
        <motion.div
          layoutId="activeGlow"
          className="absolute inset-0 rounded-xl bg-gradient-to-br from-blue-500/5 via-transparent to-indigo-500/5 pointer-events-none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        />
      )}

      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-semibold text-base leading-tight mb-1">
            {config.title}
          </h3>
          <p className="text-slate-400 text-xs leading-relaxed line-clamp-2">
            {config.description}
          </p>
        </div>
        <span
          className={`shrink-0 px-2.5 py-1 rounded-full text-[10px] font-semibold border ${
            statusColors[config.status] || statusColors.Live
          }`}
        >
          {config.status === "Live" && (
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 mr-1.5 align-middle animate-pulse" />
          )}
          {config.status}
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {config.tags.map((tag) => (
          <span
            key={tag}
            className="px-2 py-0.5 rounded-md text-[10px] font-medium bg-white/[0.06] text-slate-400 border border-white/[0.06]"
          >
            {tag}
          </span>
        ))}
      </div>

      {isSelected && (
        <motion.div
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="absolute bottom-0 left-3 right-3 h-[2px] bg-gradient-to-r from-blue-500 via-indigo-500 to-cyan-500 rounded-full origin-left"
        />
      )}
    </motion.button>
  );
}

export default function AgentCards({ selectedAgent, onSelect }) {
  return (
    <div className="space-y-3">
      {Object.values(AGENT_CONFIGS).map((config, i) => (
        <AgentCard
          key={config.id}
          config={config}
          isSelected={selectedAgent === config.id}
          onSelect={onSelect}
          index={i}
        />
      ))}
    </div>
  );
}
