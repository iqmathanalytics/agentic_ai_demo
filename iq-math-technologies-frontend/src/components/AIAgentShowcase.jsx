import { useState, useRef, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { AGENT_CONFIGS, generateMockResults } from "./agentsData";
import AgentCards from "./AgentCards";
import RightPanel from "./RightPanel";
import { Modals } from "./Modals";

const simulatedExecution = {
  stock: {
    logTimings: [400, 800, 1300, 1800, 2400, 2900, 3500, 4200],
    workflowSteps: [
      { id: "collector", start: 200, duration: 1000 },
      { id: "technical", start: 1000, duration: 1200 },
      { id: "sentiment", start: 2000, duration: 1000 },
      { id: "risk", start: 2800, duration: 800 },
      { id: "insight", start: 3500, duration: 700 },
    ],
    totalDuration: 4500,
  },
  resume: {
    logTimings: [500, 1000, 1600, 2200, 2800, 3300, 3800, 4300],
    workflowSteps: [
      { id: "parser", start: 300, duration: 1000 },
      { id: "ats", start: 1200, duration: 1000 },
      { id: "skill", start: 2000, duration: 900 },
      { id: "grammar", start: 2700, duration: 800 },
      { id: "coach", start: 3300, duration: 900 },
    ],
    totalDuration: 4500,
  },
  linkedin: {
    logTimings: [400, 900, 1500, 2100, 2800, 3500],
    workflowSteps: [
      { id: "scanner", start: 200, duration: 1000 },
      { id: "keyword", start: 1100, duration: 1000 },
      { id: "visibility", start: 2000, duration: 900 },
      { id: "engagement", start: 2700, duration: 800 },
    ],
    totalDuration: 3800,
  },
};

export default function AIAgentsShowcase() {
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [activeModal, setActiveModal] = useState(null);
  const [status, setStatus] = useState("idle");
  const [workflow, setWorkflow] = useState([]);
  const [logs, setLogs] = useState([]);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const timersRef = useRef([]);
  const startTimeRef = useRef(0);

  const clearTimers = useCallback(() => {
    timersRef.current.forEach(clearTimeout);
    timersRef.current.forEach(clearInterval);
    timersRef.current = [];
  }, []);

  useEffect(() => {
    return () => clearTimers();
  }, [clearTimers]);

  const runSimulation = useCallback(
    (agentId) => {
      clearTimers();
      const config = AGENT_CONFIGS[agentId];
      const execution = simulatedExecution[agentId];
      if (!config || !execution) return;

      const initialWorkflow = config.workflow.map((s) => ({ ...s, status: "idle" }));
      setWorkflow(initialWorkflow);
      setLogs([]);
      setProgress(0);
      setResults(null);
      setStatus("running");
      setActiveModal(null);
      startTimeRef.current = Date.now();

      execution.logTimings.forEach((delay, i) => {
        const timer = setTimeout(() => {
          setLogs((prev) => [...prev, config.logs[i]]);
        }, delay);
        timersRef.current.push(timer);
      });

      execution.workflowSteps.forEach((step) => {
        const startTimer = setTimeout(() => {
          setWorkflow((prev) =>
            prev.map((s) => (s.id === step.id ? { ...s, status: "running" } : s))
          );
        }, step.start);
        timersRef.current.push(startTimer);

        const completeTimer = setTimeout(() => {
          setWorkflow((prev) =>
            prev.map((s) => (s.id === step.id ? { ...s, status: "completed" } : s))
          );
        }, step.start + step.duration);
        timersRef.current.push(completeTimer);
      });

      const progressTimer = setInterval(() => {
        const elapsed = Date.now() - startTimeRef.current;
        const pct = Math.min(100, Math.round((elapsed / execution.totalDuration) * 100));
        setProgress(pct);
        if (pct >= 100) clearInterval(progressTimer);
      }, 100);
      timersRef.current.push(progressTimer);

      const completeTimer = setTimeout(() => {
        setStatus("completed");
        setProgress(100);
        setLogs((prev) => {
          const lastLog = config.logs[config.logs.length - 1];
          return prev.includes(lastLog) ? prev : [...prev, lastLog];
        });
        setWorkflow((prev) => prev.map((s) => ({ ...s, status: "completed" })));
        setResults(generateMockResults(config.resultType));
      }, execution.totalDuration + 200);
      timersRef.current.push(completeTimer);
    },
    [clearTimers]
  );

  const handleSelect = useCallback(
    (agentId) => {
      setSelectedAgent(agentId);
      if (status === "running") {
        clearTimers();
        setStatus("idle");
        setWorkflow([]);
        setLogs([]);
        setProgress(0);
        setResults(null);
      } else {
        setStatus("idle");
        setWorkflow([]);
        setLogs([]);
        setProgress(0);
        setResults(null);
      }
      setActiveModal(agentId);
    },
    [status, clearTimers]
  );

  const handleModalClose = useCallback(() => {
    setActiveModal(null);
  }, []);

  const handleStockSubmit = useCallback(
    (formData) => {
      runSimulation("stock");
    },
    [runSimulation]
  );

  const handleResumeSubmit = useCallback(
    (formData) => {
      runSimulation("resume");
    },
    [runSimulation]
  );

  const handleLinkedInSubmit = useCallback(
    (formData) => {
      runSimulation("linkedin");
    },
    [runSimulation]
  );

  const handleRunAgain = useCallback(() => {
    if (selectedAgent) {
      setActiveModal(selectedAgent);
    }
  }, [selectedAgent]);

  return (
    <section className="relative py-24 overflow-hidden" id="agents">
      <div className="absolute inset-0 bg-[#0B0F19]">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/5 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-indigo-500/5 rounded-full blur-[100px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-500/3 rounded-full blur-[150px]" />
      </div>

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-100px" }}
          transition={{ duration: 0.6 }}
          className="text-center mb-12"
        >
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-semibold bg-blue-500/10 text-blue-300 border border-blue-500/20 mb-4">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
            AI AGENT SHOWCASE
          </span>
          <h2 className="text-white font-bold mb-4">
            Experience AI Agents in{" "}
            <span className="bg-gradient-to-r from-blue-400 via-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              Real Time
            </span>
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto text-sm leading-relaxed">
            Watch specialized AI agents collaborate live to analyze data, review resumes, and
            generate professional insights.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-[380px_1fr] gap-6">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div className="p-4 rounded-2xl border border-white/5 bg-[#121826]/80 backdrop-blur-sm">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider font-medium mb-3 px-1">
                Agent Scenarios
              </div>
              <AgentCards selectedAgent={selectedAgent} onSelect={handleSelect} />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="min-h-[500px]"
          >
            <div className="h-full p-5 rounded-2xl border border-white/5 bg-[#121826]/80 backdrop-blur-sm">
              <RightPanel
                agentId={selectedAgent}
                status={status}
                workflow={workflow}
                logs={logs}
                progress={progress}
                results={results}
              />
              {status === "completed" && selectedAgent && (
                <motion.button
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                  onClick={handleRunAgain}
                  className="mt-4 w-full py-2.5 rounded-xl border border-white/10 bg-white/5 text-white text-sm font-medium hover:bg-white/10 transition-all"
                >
                  Run Another Analysis
                </motion.button>
              )}
            </div>
          </motion.div>
        </div>
      </div>

      <Modals
        activeModal={activeModal}
        onClose={handleModalClose}
        onStockSubmit={handleStockSubmit}
        onResumeSubmit={handleResumeSubmit}
        onLinkedInSubmit={handleLinkedInSubmit}
      />

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255,255,255,0.1);
          border-radius: 2px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255,255,255,0.2);
        }
      `}</style>
    </section>
  );
}
