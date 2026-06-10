import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AGENT_CONFIGS } from "./agentsData";

export const PROVIDER_MODELS = {
  openai: ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o"],
  gemini: ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
  claude: ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"],
  openrouter: [
    "openai/gpt-4o-mini",
    "anthropic/claude-3.5-sonnet",
    "google/gemini-flash-1.5",
    "meta-llama/llama-3.1-70b-instruct",
  ],
  groq: [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "deepseek-r1-distill-llama-70b",
    "qwen-qwq-32b",
    "gemma2-9b-it",
  ],
};

const PROVIDER_LABELS = {
  openai: "OpenAI",
  gemini: "Gemini",
  claude: "Claude",
  openrouter: "OpenRouter",
  groq: "Groq",
};

const PROVIDER_BADGES = {
  groq: "Free Tier Available",
};

const backdrop = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

const modalVariants = {
  hidden: { opacity: 0, scale: 0.92, y: 40 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { type: "spring", damping: 25, stiffness: 300 },
  },
  exit: { opacity: 0, scale: 0.95, y: 20, transition: { duration: 0.2 } },
};

function ModalWrapper({ isOpen, onClose, title, gradient, children }) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          variants={backdrop}
          initial="hidden"
          animate="visible"
          exit="hidden"
        >
          <motion.div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            className="relative w-full max-w-lg rounded-2xl border border-white/10 bg-[#0B0F19] shadow-2xl overflow-hidden"
            variants={modalVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <div className={`absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r ${gradient}`} />
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-white text-lg font-semibold">{title}</h2>
                <button
                  onClick={onClose}
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
                >
                  ✕
                </button>
              </div>
              {children}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function AIProviderModal({ isOpen, onClose, onSave }) {
  const [form, setForm] = useState({
    provider: "openai",
    model: PROVIDER_MODELS.openai[0],
    apiKey: "",
    remember: true,
  });

  const setProvider = (provider) => {
    setForm((prev) => ({
      ...prev,
      provider,
      model: PROVIDER_MODELS[provider][0],
    }));
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!form.apiKey.trim()) return;
    onSave(
      {
        provider: form.provider,
        model: form.model,
        apiKey: form.apiKey.trim(),
      },
      form.remember
    );
    setForm((prev) => ({ ...prev, apiKey: "" }));
  };

  return (
    <ModalWrapper
      isOpen={isOpen}
      onClose={onClose}
      title="Connect Your AI Model"
      gradient="from-cyan-500 to-blue-500"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <p className="text-sm text-slate-400 leading-relaxed">
          Connect your preferred AI provider to enable real-time agent execution.
        </p>

        <div>
          <label className="block text-slate-300 text-xs font-medium mb-1.5">Provider</label>
          <select
            value={form.provider}
            onChange={(event) => setProvider(event.target.value)}
            className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-blue-500/50"
          >
            {Object.entries(PROVIDER_LABELS).map(([value, label]) => (
              <option key={value} value={value} className="bg-[#121826]">
                {label}
              </option>
            ))}
          </select>
          {PROVIDER_BADGES[form.provider] && (
            <span className="mt-1.5 inline-block px-2 py-0.5 text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 rounded">
              {PROVIDER_BADGES[form.provider]}
            </span>
          )}
        </div>

        <div>
          <label className="block text-slate-300 text-xs font-medium mb-1.5">Model</label>
          <select
            value={form.model}
            onChange={(event) => setForm({ ...form, model: event.target.value })}
            className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-blue-500/50"
          >
            {PROVIDER_MODELS[form.provider].map((model) => (
              <option key={model} value={model} className="bg-[#121826]">
                {model}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-slate-300 text-xs font-medium mb-1.5">API Key</label>
          <input
            type="password"
            value={form.apiKey}
            onChange={(event) => setForm({ ...form, apiKey: event.target.value })}
            placeholder="Paste your provider API key"
            className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
            required
          />
        </div>

        <label className="flex items-center gap-2 text-xs text-slate-300">
          <input
            type="checkbox"
            checked={form.remember}
            onChange={(event) => setForm({ ...form, remember: event.target.checked })}
            className="h-4 w-4 rounded border-white/10 bg-white/5"
          />
          Remember This Device
        </label>

        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={onClose}
            className="py-3 rounded-xl border border-white/10 bg-white/5 text-slate-300 font-semibold text-sm hover:bg-white/10 transition-all"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-semibold text-sm hover:shadow-lg hover:shadow-cyan-500/20 transition-all"
          >
            Connect & Continue
          </button>
        </div>
      </form>
    </ModalWrapper>
  );
}

function SettingsModal({
  isOpen,
  onClose,
  credentials,
  apiBase,
  onDeleteKey,
  onChangeProvider,
}) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState("");

  const testConnection = async () => {
    if (!credentials) return;
    setTesting(true);
    setTestResult("");
    try {
      const response = await fetch(`${apiBase}/api/providers/test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: credentials.provider,
          model: credentials.model,
          api_key: credentials.apiKey,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Connection test failed.");
      setTestResult(data.ok ? "Connection verified." : `Provider replied: ${data.message}`);
    } catch (error) {
      setTestResult(error.message);
    } finally {
      setTesting(false);
    }
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title="AI Providers" gradient="from-blue-500 to-cyan-500">
      <div className="space-y-4">
        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs uppercase tracking-wider text-slate-500">Connection Status</span>
            <span className={`text-xs font-semibold ${credentials ? "text-emerald-400" : "text-amber-400"}`}>
              {credentials ? "● AI Connected" : "● API Key Required"}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Provider</div>
              <div className="text-white mt-1">{credentials ? PROVIDER_LABELS[credentials.provider] : "Not connected"}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-slate-500">Current Model</div>
              <div className="text-white mt-1 break-all">{credentials?.model || "Not selected"}</div>
            </div>
          </div>
        </div>

        {testResult && (
          <div className="rounded-lg border border-white/10 bg-black/30 p-3 text-xs text-slate-300">
            {testResult}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={onChangeProvider}
            className="py-2.5 rounded-xl border border-white/10 bg-white/5 text-white text-sm font-medium hover:bg-white/10"
          >
            Update Key
          </button>
          <button
            type="button"
            onClick={onChangeProvider}
            className="py-2.5 rounded-xl border border-white/10 bg-white/5 text-white text-sm font-medium hover:bg-white/10"
          >
            Change Provider
          </button>
          <button
            type="button"
            onClick={onDeleteKey}
            className="py-2.5 rounded-xl border border-red-500/20 bg-red-500/10 text-red-300 text-sm font-medium hover:bg-red-500/15"
          >
            Delete Key
          </button>
          <button
            type="button"
            disabled={!credentials || testing}
            onClick={testConnection}
            className="py-2.5 rounded-xl border border-cyan-500/20 bg-cyan-500/10 text-cyan-300 text-sm font-medium hover:bg-cyan-500/15 disabled:opacity-50"
          >
            {testing ? "Testing..." : "Test Connection"}
          </button>
        </div>
      </div>
    </ModalWrapper>
  );
}

function StockModal({ isOpen, onClose, onSubmit }) {
  const [form, setForm] = useState({
    name: "",
    symbol: "",
    exchange: "NSE",
    analyses: ["Technical Analysis"],
  });
  const config = AGENT_CONFIGS.stock;

  const toggleAnalysis = (opt) => {
    setForm((prev) => ({
      ...prev,
      analyses: prev.analyses.includes(opt)
        ? prev.analyses.filter((a) => a !== opt)
        : [...prev.analyses, opt],
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.name || !form.symbol) return;
    onSubmit(form);
    setForm({ name: "", symbol: "", exchange: "NSE", analyses: ["Technical Analysis"] });
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title={config.title} gradient={config.gradient}>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-slate-300 text-xs font-medium mb-1.5">Stock Name</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="e.g. Reliance Industries"
              className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all"
              required
            />
          </div>
          <div>
            <label className="block text-slate-300 text-xs font-medium mb-1.5">Stock Symbol</label>
            <input
              type="text"
              value={form.symbol}
              onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
              placeholder="e.g. RELIANCE"
              className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all"
              required
            />
          </div>
        </div>

        <div>
          <label className="block text-slate-300 text-xs font-medium mb-1.5">Exchange</label>
          <select
            value={form.exchange}
            onChange={(e) => setForm({ ...form, exchange: e.target.value })}
            className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all appearance-none cursor-pointer"
          >
            {config.exchanges.map((ex) => (
              <option key={ex} value={ex} className="bg-[#121826]">
                {ex}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-slate-300 text-xs font-medium mb-2">Analysis Options</label>
          <div className="grid grid-cols-2 gap-2">
            {config.analysisOptions.map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => toggleAnalysis(opt)}
                className={`px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
                  form.analyses.includes(opt)
                    ? "border-blue-500/50 bg-blue-500/10 text-blue-300"
                    : "border-white/10 bg-white/5 text-slate-400 hover:border-white/20"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          className="w-full py-3 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-white font-semibold text-sm hover:shadow-lg hover:shadow-emerald-500/20 transition-all duration-300"
        >
          Analyze Stock
        </button>
      </form>
    </ModalWrapper>
  );
}

function ResumeModal({ isOpen, onClose, onSubmit }) {
  const [form, setForm] = useState({
    file: null,
    fileName: "",
    role: "",
    experience: "Fresher",
  });
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);
  const config = AGENT_CONFIGS.resume;

  const handleFile = useCallback((file) => {
    if (file && (file.type === "application/pdf" || file.name.endsWith(".docx"))) {
      setForm((prev) => ({ ...prev, file, fileName: file.name }));
    }
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      handleFile(file);
    },
    [handleFile]
  );

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.file || !form.role) return;
    onSubmit(form);
    setForm({ file: null, fileName: "", role: "", experience: "Fresher" });
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title={config.title} gradient={config.gradient}>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-slate-300 text-xs font-medium mb-1.5">Upload Resume</label>
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`relative p-8 rounded-xl border-2 border-dashed text-center cursor-pointer transition-all ${
              isDragging
                ? "border-blue-500 bg-blue-500/5"
                : form.fileName
                  ? "border-emerald-500/40 bg-emerald-500/5"
                  : "border-white/10 bg-white/5 hover:border-white/30"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={(e) => handleFile(e.target.files[0])}
            />
            {form.fileName ? (
              <div className="text-emerald-400 text-sm font-medium">
                <span className="text-2xl block mb-2">📄</span>
                {form.fileName}
              </div>
            ) : (
              <div className="text-slate-400 text-sm">
                <span className="text-3xl block mb-2">📁</span>
                Drop your resume here or click to browse
                <div className="text-[10px] text-slate-500 mt-1">Supports PDF, DOCX</div>
              </div>
            )}
          </div>
        </div>

        <div>
          <label className="block text-slate-300 text-xs font-medium mb-1.5">Target Role</label>
          <input
            type="text"
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
            placeholder="e.g. AI Engineer"
            className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all"
            required
          />
        </div>

        <div>
          <label className="block text-slate-300 text-xs font-medium mb-1.5">Experience Level</label>
          <div className="flex gap-2">
            {config.experienceLevels.map((level) => (
              <button
                key={level}
                type="button"
                onClick={() => setForm({ ...form, experience: level })}
                className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium border transition-all ${
                  form.experience === level
                    ? "border-purple-500/50 bg-purple-500/10 text-purple-300"
                    : "border-white/10 bg-white/5 text-slate-400 hover:border-white/20"
                }`}
              >
                {level}
              </button>
            ))}
          </div>
        </div>

        <button
          type="submit"
          className="w-full py-3 rounded-xl bg-gradient-to-r from-violet-500 to-purple-500 text-white font-semibold text-sm hover:shadow-lg hover:shadow-violet-500/20 transition-all duration-300"
        >
          Analyze Resume
        </button>
      </form>
    </ModalWrapper>
  );
}

function LinkedInModal({ isOpen, onClose, onSubmit }) {
  const [url, setUrl] = useState("");
  const config = AGENT_CONFIGS.linkedin;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!url) return;
    onSubmit(url);
    setUrl("");
  };

  return (
    <ModalWrapper isOpen={isOpen} onClose={onClose} title={config.title} gradient={config.gradient}>
      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-slate-300 text-xs font-medium mb-1.5">LinkedIn Profile URL</label>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://linkedin.com/in/username"
            className="w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder-slate-500 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/20 transition-all"
            required
          />
        </div>

        <button
          type="submit"
          className="w-full py-3 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-500 text-white font-semibold text-sm hover:shadow-lg hover:shadow-blue-500/20 transition-all duration-300"
        >
          Analyze Profile
        </button>
      </form>
    </ModalWrapper>
  );
}

export function Modals({
  activeModal,
  onClose,
  credentials,
  apiBase,
  onCredentialsSave,
  onDeleteKey,
  onChangeProvider,
  onStockSubmit,
  onResumeSubmit,
  onLinkedInSubmit,
}) {
  return (
    <>
      <AIProviderModal
        isOpen={activeModal === "credentials"}
        onClose={onClose}
        onSave={onCredentialsSave}
      />
      <SettingsModal
        isOpen={activeModal === "settings"}
        onClose={onClose}
        credentials={credentials}
        apiBase={apiBase}
        onDeleteKey={onDeleteKey}
        onChangeProvider={onChangeProvider}
      />
      <StockModal isOpen={activeModal === "stock"} onClose={onClose} onSubmit={onStockSubmit} />
      <ResumeModal isOpen={activeModal === "resume"} onClose={onClose} onSubmit={onResumeSubmit} />
      <LinkedInModal isOpen={activeModal === "linkedin"} onClose={onClose} onSubmit={onLinkedInSubmit} />
    </>
  );
}
