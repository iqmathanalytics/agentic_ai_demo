import React, { useEffect, useMemo, useState } from "react";
import AIAgentsShowcase from "./components/AIAgentShowcase";

const navItems = [
  ["Overview", "#overview"],
  ["Curriculum", "#curriculum"],
  ["Outcomes", "#outcomes"],
  ["Pricing", "#pricing"],
  ["Agents", "#agents"],
  ["FAQ", "#faq"],
];

const overviewTabs = [
  {
    id: "learn",
    label: "What You Learn",
    title: "From prompts to agentic products",
    body:
      "Master prompt strategy, retrieval-augmented generation, structured outputs, multi-agent orchestration, evaluation, observability, and deployment patterns.",
    points: [
      "Build AI agents that use tools, memory, and data sources.",
      "Design workflows for math, analytics, customer support, and automation.",
      "Measure quality with rubrics, tests, traces, and human review loops.",
    ],
  },
  {
    id: "format",
    label: "Course Format",
    title: "Live, practical, and paced for working professionals",
    body:
      "Weekly live classes, guided labs, assignments, office hours, and recorded recaps help learners keep momentum without leaving their current role.",
    points: [
      "Saturday and Sunday live batches in IST.",
      "Assignment reviews and capstone checkpoints.",
      "Private community for doubt-solving and project feedback.",
    ],
  },
  {
    id: "support",
    label: "Learner Support",
    title: "Mentoring beyond the lecture",
    body:
      "IQ Math Technologies combines engineering coaching with applied math intuition, helping learners understand why systems work, not only how to call an API.",
    points: [
      "Mentor-led reviews for architecture and code quality.",
      "Career-ready portfolio guidance.",
      "Interview and freelancing use-case preparation.",
    ],
  },
];

const audienceCards = [
  ["01", "Developers", "Turn Python and API knowledge into deployed agentic applications."],
  ["02", "Data Professionals", "Connect models to data, dashboards, analytics, and decision workflows."],
  ["03", "Founders", "Prototype AI products, internal copilots, and revenue-ready automation."],
  ["04", "Educators", "Bring AI tools into math, STEM, and personalized learning experiences."],
];

const curriculum = [
  ["Week 1", "AI Engineering Foundations", "LLM behavior, model selection, prompt design, safety, and system framing."],
  ["Week 2", "Python, APIs, and Structured Outputs", "Function calling, JSON schemas, validations, and reliable response design."],
  ["Week 3", "RAG and Knowledge Systems", "Embeddings, vector search, chunking, citations, and retrieval evaluation."],
  ["Week 4", "Tool-Using Agents", "Planning, tool routing, memory, state, and workflow orchestration."],
  ["Week 5", "Multi-Agent Systems", "Role design, collaboration patterns, guardrails, handoffs, and supervision."],
  ["Week 6", "Evaluation and Observability", "Automated tests, traces, quality rubrics, cost control, and monitoring."],
  ["Week 7", "Deployment", "Frontend integration, backend services, databases, security, and hosting."],
  ["Week 8", "Capstone Showcase", "Present a working AI product with architecture, metrics, and demo flow."],
];

const outcomes = [
  ["Portfolio projects", "Ship an AI tutor, support agent, document analyst, analytics copilot, and capstone."],
  ["Certificate", "Receive a completion certificate from IQ Math Technologies after final review."],
  ["Career readiness", "Practice explaining architecture, tradeoffs, evaluation, and deployment decisions."],
];

const testimonials = [
  [
    "The projects helped me understand how agent workflows actually behave in production.",
    "Software Engineer, Bengaluru",
  ],
  [
    "The math-first explanations made RAG, embeddings, and evaluation much easier to reason about.",
    "Data Analyst, Pune",
  ],
  [
    "I went from scattered AI tutorials to a portfolio project I could explain clearly.",
    "Founder, Hyderabad",
  ],
];

const faqs = [
  [
    "Do I need advanced AI experience?",
    "Basic Python helps. The course starts with foundations and moves into advanced systems step by step.",
  ],
  [
    "Will sessions suit Indian working professionals?",
    "Yes. Live classes are planned around IST weekend slots, with recordings for revision.",
  ],
  [
    "Is this only for software developers?",
    "No. Analysts, founders, educators, and advanced students can join if they are comfortable learning technical workflows.",
  ],
  [
    "Can I pay in installments?",
    "Installment options can be discussed during the admissions callback.",
  ],
];

function Brand() {
  return (
    <a className="brand" href="#top" aria-label="IQ Math Technologies home">
      <span className="brand-mark">IQ</span>
      <span>
        <strong>IQ Math</strong>
        <small>Technologies</small>
      </span>
    </a>
  );
}

function Header() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <header className="site-header" id="top">
      <nav className="nav-shell" aria-label="Primary navigation">
        <Brand />
        <button
          className="nav-toggle"
          type="button"
          aria-expanded={isOpen}
          aria-controls="nav-links"
          onClick={() => setIsOpen((current) => !current)}
        >
          <span />
          <span />
          <span />
        </button>
        <div className={`nav-links ${isOpen ? "open" : ""}`} id="nav-links">
          {navItems.map(([label, href]) => (
            <a key={href} href={href} onClick={() => setIsOpen(false)}>
              {label}
            </a>
          ))}
          <a className="nav-cta" href="#enquiry" onClick={() => setIsOpen(false)}>
            Enroll Now
          </a>
        </div>
      </nav>
    </header>
  );
}

function Hero() {
  return (
    <section className="hero">
      <img className="hero-image" src="/assets/hero-ai-classroom.png" alt="AI engineering classroom" />
      <div className="hero-overlay" />
      <div className="hero-content">
        <p className="eyebrow">Live online cohort for Indian professionals</p>
        <h1>Agentic AI Engineering Course</h1>
        <p className="hero-copy">
          Learn to design, build, and deploy autonomous AI workflows with Python, LLMs,
          retrieval systems, tool calling, and production-grade evaluation.
        </p>
        <div className="hero-actions">
          <a className="button primary" href="#pricing">
            View Indian Pricing
          </a>
          <a className="button secondary" href="#curriculum">
            Explore Syllabus
          </a>
        </div>
        <div className="hero-meta" aria-label="Course highlights">
          {["8 weeks", "Weekend live sessions", "Capstone project", "Certificate included"].map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

function StatsBand() {
  return (
    <section className="stats-band" aria-label="Program statistics">
      {[
        ["20+", "hands-on labs"],
        ["5", "production projects"],
        ["1:1", "mentor review"],
        ["India", "timezone friendly"],
      ].map(([value, label]) => (
        <div key={label}>
          <strong>{value}</strong>
          <span>{label}</span>
        </div>
      ))}
    </section>
  );
}

function Overview() {
  const [activeTab, setActiveTab] = useState(overviewTabs[0].id);
  const selectedTab = overviewTabs.find((tab) => tab.id === activeTab) ?? overviewTabs[0];

  return (
    <section className="section" id="overview">
      <div className="section-heading">
        <p className="eyebrow">Course overview</p>
        <h2>Built for people who want to ship real AI systems.</h2>
        <p>
          This React frontend mirrors the premium course-landing structure of the reference site,
          adapted for IQ Math Technologies, Indian learners, and INR-based enrollment.
        </p>
      </div>

      <div className="tab-panel">
        <div className="tabs" role="tablist" aria-label="Course overview tabs">
          {overviewTabs.map((tab) => (
            <button
              className={`tab ${tab.id === activeTab ? "active" : ""}`}
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={tab.id === activeTab}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="tab-content active">
          <h3>{selectedTab.title}</h3>
          <p>{selectedTab.body}</p>
          <CheckList items={selectedTab.points} />
        </div>
      </div>
    </section>
  );
}

function Audience() {
  return (
    <section className="split-section">
      <div>
        <p className="eyebrow">Who should join</p>
        <h2>For learners ready to move from AI curiosity to AI capability.</h2>
        <p>
          The course fits software engineers, data analysts, teachers, founders, operations
          leaders, and advanced students who want a structured route into applied AI.
        </p>
      </div>
      <div className="feature-grid">
        {audienceCards.map(([number, title, body]) => (
          <article key={title}>
            <span>{number}</span>
            <h3>{title}</h3>
            <p>{body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function Curriculum() {
  return (
    <section className="section muted" id="curriculum">
      <div className="section-heading">
        <p className="eyebrow">Curriculum</p>
        <h2>Eight weeks of engineering depth.</h2>
      </div>
      <div className="timeline">
        {curriculum.map(([week, title, body]) => (
          <article key={week}>
            <span>{week}</span>
            <h3>{title}</h3>
            <p>{body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function Outcomes() {
  return (
    <section className="section" id="outcomes">
      <div className="section-heading">
        <p className="eyebrow">Outcomes</p>
        <h2>Graduate with proof of skill.</h2>
      </div>
      <div className="outcome-grid">
        {outcomes.map(([title, body]) => (
          <article key={title}>
            <h3>{title}</h3>
            <p>{body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function Pricing() {
  const offerEndsAt = useMemo(() => {
    const date = new Date();
    date.setDate(date.getDate() + 7);
    date.setHours(23, 59, 59, 0);
    return date;
  }, []);
  const [timeLeft, setTimeLeft] = useState(() => getTimeLeft(offerEndsAt));

  useEffect(() => {
    const interval = window.setInterval(() => {
      setTimeLeft(getTimeLeft(offerEndsAt));
    }, 60 * 1000);

    return () => window.clearInterval(interval);
  }, [offerEndsAt]);

  return (
    <section className="pricing-section" id="pricing">
      <div className="pricing-copy">
        <p className="eyebrow">Indian pricing</p>
        <h2>Enroll in the next cohort.</h2>
        <p>
          Pricing is displayed in Indian Rupees with GST-ready invoice support. Flexible
          installment support can be added during counselling.
        </p>
        <div className="countdown" aria-label="Offer countdown">
          <CountdownItem value={timeLeft.days} label="days" />
          <CountdownItem value={timeLeft.hours} label="hours" />
          <CountdownItem value={timeLeft.minutes} label="mins" />
        </div>
      </div>
      <aside className="price-card" id="enquiry">
        <p className="badge">Early bird</p>
        <h3>Agentic AI Engineering</h3>
        <div className="price">
          <span>Rs.</span>
          <strong>24,999</strong>
        </div>
        <p className="old-price">Regular fee: Rs. 39,999</p>
        <CheckList
          items={[
            "8-week live cohort",
            "All recordings and lab files",
            "Mentor feedback on projects",
            "Certificate and capstone review",
          ]}
        />
        <a className="button primary wide" href="mailto:admissions@iqmathtechnologies.com">
          Request Callback
        </a>
      </aside>
    </section>
  );
}

function Testimonials() {
  return (
    <section className="section muted">
      <div className="section-heading">
        <p className="eyebrow">Learner voices</p>
        <h2>Designed to feel practical from week one.</h2>
      </div>
      <div className="testimonial-grid">
        {testimonials.map(([quote, byline]) => (
          <blockquote key={byline}>
            <p>"{quote}"</p>
            <cite>{byline}</cite>
          </blockquote>
        ))}
      </div>
    </section>
  );
}

function FAQ() {
  const [openIndex, setOpenIndex] = useState(null);

  return (
    <section className="section faq" id="faq">
      <div className="section-heading">
        <p className="eyebrow">FAQ</p>
        <h2>Questions before you join?</h2>
      </div>
      <div className="faq-list">
        {faqs.map(([question, answer], index) => {
          const isOpen = openIndex === index;

          return (
            <div className="faq-row" key={question}>
              <button className="faq-item" type="button" onClick={() => setOpenIndex(isOpen ? null : index)}>
                <span>{question}</span>
                <strong>{isOpen ? "-" : "+"}</strong>
              </button>
              <div className={`faq-answer ${isOpen ? "open" : ""}`}>{answer}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="footer">
      <div>
        <Brand />
        <p>Applied AI, mathematics, and engineering education for modern teams.</p>
      </div>
      <div className="footer-links">
        {navItems.slice(0, 4).map(([label, href]) => (
          <a key={href} href={href}>
            {label}
          </a>
        ))}
        <a href="mailto:admissions@iqmathtechnologies.com">Contact</a>
      </div>
    </footer>
  );
}

function CheckList({ items }) {
  return (
    <ul className="check-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function CountdownItem({ value, label }) {
  return (
    <span>
      <strong>{String(value).padStart(2, "0")}</strong>
      {label}
    </span>
  );
}

function getTimeLeft(targetDate) {
  const remaining = Math.max(0, targetDate - new Date());

  return {
    days: Math.floor(remaining / (1000 * 60 * 60 * 24)),
    hours: Math.floor((remaining / (1000 * 60 * 60)) % 24),
    minutes: Math.floor((remaining / (1000 * 60)) % 60),
  };
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("React Crash caught by ErrorBoundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center p-6">
          <div className="max-w-md w-full p-8 rounded-3xl border border-rose-500/20 bg-rose-500/5 text-center">
            <div className="text-4xl mb-6">⚠️</div>
            <h2 className="text-white font-bold text-xl mb-3">Agent execution failed</h2>
            <p className="text-slate-400 text-sm mb-6 leading-relaxed">
              The application encountered an unexpected error. This usually happens when the agent returns data in an unrecognized format.
            </p>
            <div className="p-4 rounded-xl bg-black/40 border border-white/5 text-left mb-6 overflow-x-auto">
              <code className="text-[10px] text-rose-300 font-mono whitespace-pre">
                {this.state.error?.toString()}
              </code>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="w-full py-3 rounded-xl bg-white/10 text-white text-sm font-bold hover:bg-white/20 transition-all"
            >
              Reload Application
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <Header />
      <main>
        <Hero />
        <StatsBand />
        <Overview />
        <Audience />
        <Curriculum />
        <Outcomes />
        <Pricing />
        <Testimonials />
        <AIAgentsShowcase />
        <FAQ />
      </main>
      <Footer />
    </ErrorBoundary>
  );
}
