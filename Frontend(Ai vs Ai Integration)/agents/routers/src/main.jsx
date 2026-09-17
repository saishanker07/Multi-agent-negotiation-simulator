import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = "/api";

const fallbackScenarios = { 1: "Land / Plot", 2: "Apartment / Flat", 3: "Villa / Independent House" };
const fallbackPersonalities = { 1: "Aggressive", 2: "Collaborative", 3: "Risk-Averse" };
const personalityMeta = {
  aggressive: { label: "Aggressive", icon: "⚡" },
  collaborative: { label: "Collaborative", icon: "🤝" },
  risk_averse: { label: "Risk-Averse", icon: "🛡️" },
};

const money = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(number);
};

const prettyKey = (key) => String(key).replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

const getValue = (obj, names) => {
  if (!obj) return null;
  const key = Object.keys(obj).find((k) => names.some((name) => k.toLowerCase() === name.toLowerCase()));
  return key ? obj[key] : null;
};

function normalizePersonality(value) {
  return String(value ?? "").toLowerCase().replace(/-/g, "_").replace(/ /g, "_");
}

function extractOffer(text) {
  if (!text) return null;
  const raw = String(text);
  let match = raw.match(/₹\s*([\d,]+(?:\.\d+)?)\s*(?:crores?|crore)\b/i);
  if (match) return Number(match[1].replace(/,/g, "")) * 10000000;
  match = raw.match(/₹?\s*([\d,]+(?:\.\d+)?)\s*(?:lakhs?|lakh|L)\b/i);
  if (match) return Number(match[1].replace(/,/g, "")) * 100000;
  match = raw.match(/₹\s*([\d,]+(?:\.\d+)?)/);
  return match ? Number(match[1].replace(/,/g, "")) : null;
}

function decisionFromText(text) {
  const value = String(text || "").toUpperCase();
  if (value.includes("DEADLOCK")) return "DEADLOCK";
  if (value.includes("ACCEPT")) return "ACCEPT";
  if (value.includes("REJECT")) return "REJECT";
  if (value.includes("COUNTER")) return "COUNTER";
  return "";
}

function App() {
  const [mode, setMode] = useState("human-ai");
  const [scenarios, setScenarios] = useState(fallbackScenarios);
  const [personalities, setPersonalities] = useState(fallbackPersonalities);
  const [properties, setProperties] = useState([]);

  const [scenario, setScenario] = useState(2);
  const [propertyIndex, setPropertyIndex] = useState(0);
  const [humanRole, setHumanRole] = useState("buyer");
  const [aiPersonality, setAiPersonality] = useState("collaborative");
  const [buyerPersonality, setBuyerPersonality] = useState(2);
  const [sellerPersonality, setSellerPersonality] = useState(2);
  const [maxRounds, setMaxRounds] = useState(10);

  const [session, setSession] = useState(null);
  const [message, setMessage] = useState("");
  const [offer, setOffer] = useState("");
  const [loading, setLoading] = useState(false);
  const [propertiesLoading, setPropertiesLoading] = useState(false);
  const [error, setError] = useState("");

  const selectedProperty = useMemo(() => properties.find((p) => p.index === Number(propertyIndex)), [properties, propertyIndex]);
  const propertyData = selectedProperty?.property || session?.property || {};
  const status = session?.status || "ready";

  useEffect(() => { loadMetadata(); }, []);
  useEffect(() => { loadProperties(scenario); }, [scenario]);

  async function loadMetadata() {
    try {
      const [scenarioRes, personalityRes] = await Promise.all([fetch(`${API}/scenarios`), fetch(`${API}/personalities`)]);
      if (scenarioRes.ok) setScenarios((await scenarioRes.json()).scenarios || fallbackScenarios);
      if (personalityRes.ok) setPersonalities((await personalityRes.json()).personalities || fallbackPersonalities);
    } catch {
      // Fallback metadata keeps the UI usable while the backend is starting.
    }
  }

  async function loadProperties(selectedScenario) {
    setPropertiesLoading(true);
    setError("");
    try {
      const response = await fetch(`${API}/properties?scenario=${selectedScenario}&start=0&limit=100`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to load properties.");
      setProperties(data.properties || []);
      setPropertyIndex(0);
    } catch (err) {
      setProperties([]);
      setError(`${err.message} Start the FastAPI backend on http://127.0.0.1:8000.`);
    } finally {
      setPropertiesLoading(false);
    }
  }

  function resetSession() {
    setSession(null);
    setMessage("");
    setOffer("");
    setError("");
  }

  async function startHumanNegotiation() {
    setLoading(true); setError(""); setSession(null); setMessage(""); setOffer("");
    try {
      const response = await fetch(`${API}/negotiations/practice`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario: Number(scenario), property_index: Number(propertyIndex), human_role: humanRole, ai_personality: aiPersonality, max_rounds: Number(maxRounds) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not start negotiation.");
      setSession({ ...data, history: [{ round: 0, sender: `ai_${data.ai_role}`, message: data.ai_message, decision: "INITIAL_GREETING", offer: data.ai_role === "seller" ? getValue(data.property, ["Price", "price", "Selling Price", "selling_price"]) : null }] });
    } catch (err) { setError(err.message); } finally { setLoading(false); }
  }

  async function startAiVsAi() {
    setLoading(true); setError(""); setSession(null); setMessage(""); setOffer("");
    try {
      const response = await fetch(`${API}/negotiations`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario: Number(scenario), buyer_personality: Number(buyerPersonality), seller_personality: Number(sellerPersonality), property_index: Number(propertyIndex), max_rounds: Number(maxRounds) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not start AI-vs-AI simulation.");
      const history = (data.negotiation_history || []).map((item, index) => ({
        ...item,
        id: `${index}-${item.round}`,
        sender: item.agent === "Buyer Agent" ? "ai_buyer" : "ai_seller",
        offer: extractOffer(item.message),
        decision: decisionFromText(item.message),
      }));
      setSession({ ...data, mode: "ai_vs_ai", history, round: Math.max(1, ...(history.map((h) => Number(h.round) || 1))), max_rounds: Number(maxRounds), reference_price: getValue(data.property, ["Price", "price", "Selling Price", "selling_price"]), buyer_personality: data.buyer_personality, seller_personality: data.seller_personality, latestDecision: history.length ? history[history.length - 1] : null });
    } catch (err) { setError(err.message); } finally { setLoading(false); }
  }

  async function startNegotiation() {
    if (mode === "ai-ai") return startAiVsAi();
    return startHumanNegotiation();
  }

  async function sendMessage(event) {
    event?.preventDefault();
    if (!session || session.status !== "active" || !message.trim()) return;
    setLoading(true); setError("");
    try {
      const response = await fetch(`${API}/negotiations/${session.negotiation_id}/message`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: message.trim(), offer: offer === "" ? null : Number(offer) }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to send message.");
      const humanEntry = { round: data.round, sender: `human_${session.human_role}`, message: data.human_message, offer: data.human_offer };
      const aiEntry = { round: data.round, sender: `ai_${session.ai_role}`, message: data.ai_response.message, offer: data.ai_response.counter_offer, decision: data.ai_response.decision, reason: data.ai_response.reason };
      setSession((prev) => ({ ...prev, status: data.status, history: [...(prev.history || []), humanEntry, aiEntry], latestDecision: data.ai_response, round: data.round }));
      setMessage(""); setOffer("");
    } catch (err) { setError(err.message); } finally { setLoading(false); }
  }

  async function cancelNegotiation() {
    if (!session || session.mode === "ai_vs_ai") return;
    setLoading(true); setError("");
    try {
      const response = await fetch(`${API}/negotiations/${session.negotiation_id}/cancel`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to cancel negotiation.");
      setSession((prev) => ({ ...prev, status: data.status, history: [...(prev.history || []), { round: prev.round, sender: "system", message: data.message }] }));
    } catch (err) { setError(err.message); } finally { setLoading(false); }
  }

  async function refreshState() {
    if (!session || session.mode === "ai_vs_ai") return;
    try {
      const response = await fetch(`${API}/negotiations/${session.negotiation_id}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to refresh state.");
      setSession((prev) => ({ ...prev, ...data }));
    } catch (err) { setError(err.message); }
  }

  const isAiVsAi = mode === "ai-ai";
  const buyerLabel = isAiVsAi ? (typeof session?.buyer_personality === "string" ? session.buyer_personality : personalities[buyerPersonality]) : (humanRole === "buyer" ? "Human" : "Human");
  const sellerLabel = isAiVsAi ? (typeof session?.seller_personality === "string" ? session.seller_personality : personalities[sellerPersonality]) : (humanRole === "seller" ? "Human" : personalityMeta[normalizePersonality(aiPersonality)]?.label || aiPersonality);
  const buyerLast = isAiVsAi ? [...(session?.history || [])].reverse().find((h) => h.sender === "ai_buyer" && h.offer != null)?.offer : null;
  const sellerLast = isAiVsAi ? [...(session?.history || [])].reverse().find((h) => h.sender === "ai_seller" && h.offer != null)?.offer : null;
  const latestDecision = session?.latestDecision;

  return (
    <div className="app-shell">
      <header className="topbar">
        <div><div className="eyebrow">AI REAL ESTATE SIMULATION</div><h1>Negotiation Arena</h1><p>Train negotiation skills with human and autonomous AI agents.</p></div>
        <div className={`status-pill ${String(status).toLowerCase()}`}><span className="status-dot" />{String(status).replaceAll("_", " ").toUpperCase()}</div>
      </header>

      {error && <div className="error-banner"><strong>Backend message:</strong> {error}</div>}

      <main className="layout">
        <aside className="sidebar">
          <section className="panel setup-panel">
            <div className="panel-title"><span>01</span> Negotiation setup</div>

            <div className="mode-switch">
              <button className={!isAiVsAi ? "selected" : ""} onClick={() => { setMode("human-ai"); resetSession(); }}>Human vs AI</button>
              <button className={isAiVsAi ? "selected" : ""} onClick={() => { setMode("ai-ai"); resetSession(); }}>AI vs AI</button>
            </div>

            <div className="mode-description">
              {isAiVsAi ? "Two autonomous agents negotiate using separate personalities and the multi-agent orchestrator." : "You negotiate directly with an AI agent using natural-language messages and offers."}
            </div>

            <label>Scenario
              <select value={scenario} onChange={(e) => { setScenario(Number(e.target.value)); resetSession(); }}>
                {Object.entries(scenarios).map(([key, value]) => <option key={key} value={key}>{value}</option>)}
              </select>
            </label>

            <label>Property
              <select value={propertyIndex} disabled={propertiesLoading || properties.length === 0} onChange={(e) => setPropertyIndex(Number(e.target.value))}>
                {properties.map((item) => { const title = getValue(item.property, ["Property Title", "Name", "Property Name"]) || `Property ${item.index + 1}`; return <option key={item.index} value={item.index}>{item.index + 1}. {title}</option>; })}
              </select>
            </label>

            {!isAiVsAi ? <>
              <label>Your role
                <div className="segmented"><button className={humanRole === "buyer" ? "selected" : ""} onClick={() => setHumanRole("buyer")}>Buyer</button><button className={humanRole === "seller" ? "selected" : ""} onClick={() => setHumanRole("seller")}>Seller</button></div>
              </label>
              <label>AI personality
                <select value={aiPersonality} onChange={(e) => setAiPersonality(e.target.value)}>
                  {Object.entries(personalities).map(([key, value]) => <option key={key} value={normalizePersonality(value)}>{value}</option>)}
                </select>
              </label>
            </> : <>
              <label>Buyer AI personality
                <select value={buyerPersonality} onChange={(e) => setBuyerPersonality(Number(e.target.value))}>{Object.entries(personalities).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select>
              </label>
              <label>Seller AI personality
                <select value={sellerPersonality} onChange={(e) => setSellerPersonality(Number(e.target.value))}>{Object.entries(personalities).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select>
              </label>
            </>}

            <label>Maximum rounds
              <input type="number" min="1" max="50" value={maxRounds} onChange={(e) => setMaxRounds(e.target.value)} />
            </label>

            <button className="primary-btn" onClick={startNegotiation} disabled={loading || properties.length === 0}>{loading && !session ? (isAiVsAi ? "Running simulation..." : "Starting...") : isAiVsAi ? "Start AI simulation →" : "Start negotiation →"}</button>
            {session && !isAiVsAi && <button className="secondary-btn" onClick={refreshState} disabled={loading}>Refresh state</button>}
            {session && <button className="secondary-btn" onClick={resetSession}>New session</button>}
          </section>

          <section className="panel property-panel">
            <div className="panel-title"><span>02</span> Property snapshot</div>
            <h2>{getValue(propertyData, ["Property Title", "Name", "Property Name"]) || "Selected property"}</h2>
            <div className="property-price">{money(getValue(propertyData, ["Price", "price", "Selling Price", "selling_price", "Property Price"]))}</div>
            <div className="location">📍 {getValue(propertyData, ["Location", "location", "Address", "address"]) || "Location not provided"}</div>
            <div className="property-grid">{Object.entries(propertyData).filter(([key]) => !["Price", "price"].includes(key)).slice(0, 8).map(([key, value]) => <div className="property-field" key={key}><span>{prettyKey(key)}</span><strong>{String(value ?? "—")}</strong></div>)}</div>
          </section>
        </aside>

        <section className="arena">
          <div className="arena-header"><div><div className="eyebrow">{isAiVsAi ? "AUTONOMOUS SIMULATION" : "LIVE SESSION"}</div><h2>{session ? (isAiVsAi ? "AI vs AI negotiation" : `Session #${session.negotiation_id}`) : "Set up your negotiation"}</h2></div>{session && <div className="round-badge">Round {session.round || 1} / {session.max_rounds || maxRounds}</div>}</div>

          <div className="agents-row">
            <AgentCard role="buyer" name={isAiVsAi ? "Buyer AI" : humanRole === "buyer" ? "You" : "AI Buyer"} personality={buyerLabel} active={Boolean(session)} autonomous={isAiVsAi} />
            <div className="versus">VS</div>
            <AgentCard role="seller" name={isAiVsAi ? "Seller AI" : humanRole === "seller" ? "You" : "AI Seller"} personality={sellerLabel} active={Boolean(session)} autonomous={isAiVsAi} />
          </div>

          {isAiVsAi && <div className="simulation-banner"><span className="pulse-dot" /> Autonomous agents are negotiating. The backend orchestrator controls the turn order, evaluators control prices, and the reasoning engine generates responses.</div>}

          <div className="transcript panel">
            <div className="transcript-head"><div><h3>Negotiation transcript</h3><span>{session ? (isAiVsAi ? "Buyer and Seller AI messages are returned from the multi-agent simulation." : "Every offer and AI decision appears here.") : "Start a session to begin the conversation."}</span></div>{session && !isAiVsAi && <button className="cancel-btn" onClick={cancelNegotiation} disabled={loading || status !== "active"}>End session</button>}</div>
            <div className="messages">
              {!session ? <div className="empty-state"><div className="empty-icon">💬</div><h3>Ready when you are</h3><p>{isAiVsAi ? "Choose two AI personalities and run an autonomous property negotiation." : "Choose a property, role and AI personality, then start the negotiation."}</p></div> : session.history?.map((item, index) => <MessageBubble key={item.id || `${index}-${item.timestamp || ""}`} item={item} humanRole={session.human_role} aiRole={session.ai_role} aiVsAi={isAiVsAi} />)}
            </div>
            {session && !isAiVsAi && status === "active" && <form className="composer" onSubmit={sendMessage}><div className="offer-input"><span>₹</span><input type="number" min="0" placeholder="Offer amount (optional)" value={offer} onChange={(e) => setOffer(e.target.value)} /></div><input className="message-input" placeholder={humanRole === "buyer" ? "Write your offer or negotiation message..." : "Write your asking price or negotiation message..."} value={message} onChange={(e) => setMessage(e.target.value)} /><button className="send-btn" disabled={loading || !message.trim()}>{loading ? "..." : "Send"}</button></form>}
            {session && isAiVsAi && <div className={`result-banner ${String(status).toLowerCase()}`}><strong>{formatStatus(status)}</strong><span>{session.agreed_price != null ? ` Final agreed price: ${money(session.agreed_price)}.` : " The autonomous simulation has completed."}</span></div>}
            {session && !isAiVsAi && status !== "active" && <div className={`result-banner ${status}`}><strong>Negotiation {status}.</strong>{latestDecision?.message ? " Review the final AI decision above." : " Start a new session to negotiate again."}</div>}
          </div>
        </section>

        <aside className="rightbar">
          <section className="panel reasoning-panel">
            <div className="panel-title"><span>03</span> AI reasoning</div>
            {latestDecision ? <>
              <div className={`decision ${String(latestDecision.decision || decisionFromText(latestDecision.message)).toLowerCase()}`}>{latestDecision.decision || decisionFromText(latestDecision.message) || "RESPONSE"}</div>
              <h3>{isAiVsAi ? "Latest agent analysis" : "Decision analysis"}</h3>
              <p>{latestDecision.reason || (isAiVsAi ? latestDecision.message : "The AI did not return a reasoning summary for this response.")}</p>
              <div className="decision-price"><span>{isAiVsAi ? "Latest offer" : "Counter offer"}</span><strong>{money(latestDecision.counter_offer ?? latestDecision.offer ?? extractOffer(latestDecision.message))}</strong></div>
            </> : <div className="reasoning-empty"><span>◎</span><p>Once an AI responds, its decision, offer and reasoning will appear here.</p></div>}
          </section>

          <section className="panel metrics-panel">
            <div className="panel-title"><span>04</span> Negotiation metrics</div>
            <Metric label="Reference price" value={money(session?.reference_price || getValue(propertyData, ["Price", "price"]))} />
            {isAiVsAi ? <><Metric label="Latest buyer offer" value={money(buyerLast)} /><Metric label="Latest seller offer" value={money(sellerLast)} /></> : <><Metric label="Current offer" value={money(session?.current_offer)} /><Metric label="Last human offer" value={money(session?.last_human_offer)} /><Metric label="Last AI offer" value={money(session?.last_ai_offer)} /></>}
            <Metric label="Agreed price" value={money(session?.agreed_price)} />
            <Metric label="Rounds" value={session?.round || 0} />
            {!isAiVsAi && <Metric label="Stagnant rounds" value={session?.stagnant_round_count ?? 0} />}
          </section>

          {isAiVsAi && <section className="panel ai-stack-panel"><div className="panel-title"><span>05</span> Multi-agent pipeline</div><PipelineStep title="Orchestrator" text="Controls Buyer → Seller turn order" /><PipelineStep title="Reasoning engine" text="Generates agent negotiation responses" /><PipelineStep title="Counteroffer evaluator" text="Calculates the next valid price" /><PipelineStep title="Deadlock detector" text="Checks for stalled negotiations" /></section>}

          <section className="panel tip-panel"><div className="tip-icon">✦</div><div><strong>{isAiVsAi ? "Demo tip" : "Negotiation tip"}</strong><p>{isAiVsAi ? "Use this mode in the final demo to show autonomous agent interaction without manual input." : "Make a clear numerical offer when possible. The backend can also extract an offer from your natural-language message."}</p></div></section>
        </aside>
      </main>
    </div>
  );
}

function formatStatus(value) { return String(value || "").replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase()); }

function AgentCard({ role, name, personality, active, autonomous }) {
  const meta = personalityMeta[normalizePersonality(personality)] || { label: personality, icon: autonomous ? "◈" : "◎" };
  return <div className={`agent-card ${active ? "active" : ""} ${autonomous ? "autonomous" : ""}`}><div className={`avatar ${role}`}>{role === "buyer" ? "B" : "S"}</div><div><span className="agent-role">{role} {autonomous ? "· AI AGENT" : ""}</span><strong>{name}</strong><small>{meta.icon} {meta.label}</small></div></div>;
}

function MessageBubble({ item, humanRole, aiRole, aiVsAi }) {
  const sender = String(item.sender || item.agent || "");
  const isSystem = sender === "system";
  if (isSystem) return <div className="system-message"><span>•</span> {item.message}</div>;
  const isBuyer = sender.includes("buyer") || sender === "Buyer Agent";
  const isHuman = sender.startsWith("human");
  const label = aiVsAi ? (isBuyer ? "Buyer AI" : "Seller AI") : isHuman ? "You" : `AI ${aiRole}`;
  const decision = item.decision || decisionFromText(item.message);
  return <div className={`message-row ${isHuman ? "human" : isBuyer ? "buyer-agent" : "seller-agent"}`}><div className="message-meta"><span>{label}</span><span>Round {item.round}</span></div><div className="bubble"><p>{item.message}</p>{item.offer !== null && item.offer !== undefined && <div className="offer-chip">{isHuman ? "Offer" : "Offer"} · {money(item.offer)}</div>}</div>{decision && decision !== "INITIAL_GREETING" && <div className={`inline-decision ${decision.toLowerCase()}`}>{decision}</div>}{item.reason && <div className="inline-reason">{item.reason}</div>}</div>;
}

function Metric({ label, value }) { return <div className="metric"><span>{label}</span><strong>{value}</strong></div>; }
function PipelineStep({ title, text }) { return <div className="pipeline-step"><span className="pipeline-dot" /><div><strong>{title}</strong><small>{text}</small></div></div>; }

createRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);
