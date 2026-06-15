import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { AGENT_CONFIGS } from "./agentsData";
import AgentCards from "./AgentCards";
import RightPanel from "./RightPanel";
import { Modals, PROVIDER_MODELS } from "./Modals";

const API_BASE = import.meta.env.VITE_AGENT_API_URL;
const WS_BASE = API_BASE.replace(/^http/, "ws");

function loadCredentials() {
  if (typeof window === "undefined") return null;
  const provider = localStorage.getItem("llm_provider");
  const apiKey = localStorage.getItem("llm_api_key");
  const model = localStorage.getItem("llm_model");
  return provider && apiKey && model ? { provider, apiKey, model } : null;
}

function saveCredentials(credentials, remember = true) {
  if (!remember) return;
  localStorage.setItem("llm_provider", credentials.provider);
  localStorage.setItem("llm_api_key", credentials.apiKey);
  localStorage.setItem("llm_model", credentials.model);
}

function clearCredentials() {
  localStorage.removeItem("llm_provider");
  localStorage.removeItem("llm_api_key");
  localStorage.removeItem("llm_model");
}

function initialWorkflow(agentId) {
  const config = AGENT_CONFIGS[agentId];
  return config ? config.workflow.map((step) => ({ ...step, status: "idle" })) : [];
}

function nowLine(message) {
  return `[${new Date().toLocaleTimeString([], { hour12: false })}] ${message}`;
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export default function AIAgentsShowcase() {
  const [selectedAgent, setSelectedAgent] = useState(null);
  const [activeModal, setActiveModal] = useState(null);
  const [pendingAgent, setPendingAgent] = useState(null);
  const [credentials, setCredentials] = useState(null);
  const [status, setStatus] = useState("idle");
  const [workflow, setWorkflow] = useState([]);
  const [logs, setLogs] = useState([nowLine("Agent runtime ready. Select a workflow to begin.")]);
  const [progress, setProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [screenshot, setScreenshot] = useState(null);
  const [lastError, setLastError] = useState("");
  const [creditAlert, setCreditAlert] = useState("");
  const [backendConnected, setBackendConnected] = useState(false);
  const socketRef = useRef(null);

  useEffect(() => {
    setCredentials(loadCredentials());
    checkBackendHealth();
    return () => socketRef.current?.close();
  }, []);

  async function checkBackendHealth() {
    try {
      const resp = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(5000) });
      const ok = resp.ok;
      console.log("[HealthCheck] Backend at", API_BASE, ok ? "CONNECTED" : "UNREACHABLE", `(status ${resp.status})`);
      setBackendConnected(ok);
    } catch (err) {
      console.error("[HealthCheck] Backend at", API_BASE, "NOT CONNECTED —", err.message);
      setBackendConnected(false);
    }
  }

  const providerStatus = useMemo(
    () => (credentials ? `AI Connected: ${credentials.provider} / ${credentials.model}` : "API Key Required"),
    [credentials]
  );

  const appendLog = useCallback((message) => {
    if (!message) return;
    setLogs((prev) => [...prev.slice(-80), message]);
  }, []);

  const updateStep = useCallback((event) => {
    if (!event.agent_id || !event.status) return;
    setWorkflow((prev) =>
      prev.map((step) => (step.id === event.agent_id ? { ...step, status: event.status } : step))
    );
  }, []);

  const handleRuntimeAuthError = useCallback((message) => {
    const text = String(message || "").toLowerCase();
    if (text.includes("api key") || text.includes("unauthorized") || text.includes("auth")) {
      clearCredentials();
      setCredentials(null);
      setActiveModal("credentials");
    }
  }, []);

  const runAgent = useCallback(
    async (agentId, input) => {
      const activeCredentials = loadCredentials();
      if (!activeCredentials) {
        setPendingAgent(agentId);
        setActiveModal("credentials");
        return;
      }

      socketRef.current?.close();
      setSelectedAgent(agentId);
      setActiveModal(null);
      setStatus("running");
      setWorkflow(initialWorkflow(agentId));
      setLogs([nowLine("Connecting to FastAPI agent runtime...")]);
      setProgress(1);
      setResults(null);
      setScreenshot(null);
      setLastError("");
      setCreditAlert("");

      const normalizedInput = { ...input };
      if (agentId === "resume" && input.file) {
        normalizedInput.fileName = input.file.name;
        normalizedInput.fileData = await readFileAsDataUrl(input.file);
        delete normalizedInput.file;
      }

      const socket = new WebSocket(`${WS_BASE}/ws/agents`);
      socketRef.current = socket;

      socket.onopen = () => {
        appendLog(nowLine("WebSocket connected. Dispatching agent graph..."));
        socket.send(
          JSON.stringify({
            agent: agentId,
            credentials: {
              provider: activeCredentials.provider,
              model: activeCredentials.model,
              api_key: activeCredentials.apiKey,
            },
            input: normalizedInput,
          })
        );
      };

      socket.onmessage = (message) => {
        try {
          console.log("WS MESSAGE:", message.data);
          const event = JSON.parse(message.data);
          if (event.message) appendLog(event.message);
          if (typeof event.progress === "number" && event.progress > 0) setProgress(event.progress);
          if (event.type === "agent_started" || event.type === "agent_running" || event.type === "agent_completed" || event.type === "agent_failed") {
            updateStep(event);
          }
          if (event.type === "preview") {
            setScreenshot(event.payload?.preview || null);
          }
          if (event.type === "final" || event.type === "run_completed") {
            const result = event.payload?.result;
            if (result) {
              console.log("API RESPONSE", result);
              setResults(result);
            }
            setStatus("completed");
            setProgress(100);
            if (event.type === "run_completed") {
              console.log("[Agent] Workflow completed successfully");
            }
          }
          if (event.type === "run_failed" || event.type === "agent_failed") {
            console.warn("[Agent] Workflow failed:", event.message);
            setStatus("failed");
            const msg = (event.message || "").toLowerCase();
            if (msg.includes("credit") || msg.includes("402") || msg.includes("token") || msg.includes("quota") || msg.includes("rate limit") || msg.includes("insufficient")) {
              setCreditAlert(event.message);
            }
            handleRuntimeAuthError(event.message);
            setLastError("");
          }
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err, message.data);
        }
      };

      socket.onerror = () => {
        console.warn("[WebSocket] Connection error — backend unreachable at", WS_BASE);
        setBackendConnected(false);
        setStatus("failed");
        appendLog(nowLine(`Runtime connection failed. Backend expected at ${API_BASE}.`));
      };

      socket.onclose = () => {
        socketRef.current = null;
      };
    },
    [appendLog, handleRuntimeAuthError, updateStep]
  );

  const handleSelect = useCallback(
    (agentId) => {
      socketRef.current?.close();
      setSelectedAgent(agentId);
      setPendingAgent(agentId);
      setStatus("idle");
      setWorkflow(initialWorkflow(agentId));
      setProgress(0);
      setResults(null);
      setLastError("");
      setCreditAlert("");
      setLogs([nowLine(`${AGENT_CONFIGS[agentId].title} workspace opened.`)]);

      if (!loadCredentials()) {
        setActiveModal("credentials");
      } else {
        setActiveModal(agentId);
      }
    },
    []
  );

  const handleCredentialsSave = useCallback(
    (nextCredentials, remember) => {
      saveCredentials(nextCredentials, remember);
      setCredentials(nextCredentials);
      const nextAgent = pendingAgent || selectedAgent;
      setActiveModal(nextAgent || null);
    },
    [pendingAgent, selectedAgent]
  );

  const handleDismissCreditAlert = useCallback(() => {
    setCreditAlert("");
  }, []);

  const handleDeleteKey = useCallback(() => {
    clearCredentials();
    setCredentials(null);
    setLastError("");
  }, []);

  const handleStockSubmit = useCallback((formData) => runAgent("stock", formData), [runAgent]);
  const handleResumeSubmit = useCallback((formData) => runAgent("resume", formData), [runAgent]);
  const handleWebsiteAuditSubmit = useCallback((formData) => runAgent("website_audit", formData), [runAgent]);

  const handleRunAgain = useCallback(() => {
    if (!selectedAgent) return;
    if (!loadCredentials()) setActiveModal("credentials");
    else setActiveModal(selectedAgent);
  }, [selectedAgent]);

  return (
    <section className="relative py-24 overflow-hidden" id="agents">
      <div className="absolute inset-0 bg-[#0B0F19]">
        <div className="absolute inset-0 opacity-[0.08] bg-[linear-gradient(rgba(255,255,255,.09)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.09)_1px,transparent_1px)] bg-[size:36px_36px]" />
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
            Connect your LLM provider and run live LangGraph-style AI workflows with streaming
            execution logs, pipeline state, and professional reports.
          </p>
        </motion.div>

        <div className="grid lg:grid-cols-[320px_1fr] gap-6">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div className="p-4 rounded-2xl border border-white/5 bg-[#121826]/80 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-3 px-1">
                <div className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">
                  Agent Scenarios
                </div>
                <button
                  type="button"
                  onClick={() => setActiveModal("settings")}
                  className="text-[10px] text-cyan-300 border border-cyan-400/20 bg-cyan-400/10 rounded-lg px-2 py-1 hover:bg-cyan-400/15 transition-colors"
                >
                  AI Providers
                </button>
              </div>
              <AgentCards selectedAgent={selectedAgent} onSelect={handleSelect} />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="min-h-[640px]"
          >
            <div className="h-full p-5 rounded-2xl border border-white/5 bg-[#121826]/80 backdrop-blur-sm">
              <RightPanel
                agentId={selectedAgent}
                status={status}
                workflow={workflow}
                logs={logs}
                progress={progress}
                results={results}
                screenshot={screenshot}
                providerStatus={providerStatus}
                backendConnected={backendConnected}
                lastError={lastError}
                creditAlert={creditAlert}
                onDismissCreditAlert={handleDismissCreditAlert}
                onOpenSettings={() => setActiveModal("settings")}
              />
              {(status === "completed" || status === "failed") && selectedAgent && (
                <motion.button
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
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
        credentials={credentials}
        providerModels={PROVIDER_MODELS}
        apiBase={API_BASE}
        onClose={() => setActiveModal(null)}
        onCredentialsSave={handleCredentialsSave}
        onDeleteKey={handleDeleteKey}
        onChangeProvider={() => setActiveModal("credentials")}
        onStockSubmit={handleStockSubmit}
        onResumeSubmit={handleResumeSubmit}
        onWebsiteAuditSubmit={handleWebsiteAuditSubmit}
      />

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
      `}</style>
    </section>
  );
}
