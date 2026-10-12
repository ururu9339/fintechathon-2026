"use client";

import { useEffect, useState } from "react";

type ForecastPoint = { week: number; closing_balance: number; lower_bound: number; upper_bound: number };
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [forecast, setForecast] = useState<ForecastPoint[]>([]);
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("Try the prompt-injection demo below.");

  useEffect(() => {
    fetch(`${API}/api/forecast`).then((response) => response.json()).then((data) => setForecast(data.points));
  }, []);

  async function askAgent() {
    const response = await fetch(`${API}/api/agent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const data = await response.json();
    setReply(data.message);
  }

  return (
    <main>
      <header><div><span className="eyebrow">AMANAH FINTECH</span><h1>AmanahPay Treasurer</h1><p>Your cash-flow co-pilot with owner-controlled autonomy.</p></div><span className="status">● Demo environment</span></header>
      <section className="grid">
        <article className="card hero"><span className="eyebrow">13-WEEK OUTLOOK</span><h2>Know the gap before it arrives.</h2><p>Probabilistic cash-flow signals turn late invoices into an actionable plan.</p><div className="chart">{forecast.map((point) => <div className="bar-wrap" key={point.week}><div className={`bar ${point.closing_balance < 0 ? "negative" : ""}`} style={{ height: `${Math.max(12, Math.min(100, Math.abs(point.closing_balance) / 300))}%` }} /><small>W{point.week}</small></div>)}</div></article>
        <article className="card"><span className="eyebrow">ENVELOPES</span><h2>Protected funds</h2><div className="row"><span>SST & taxes</span><strong>MYR 5,200</strong></div><div className="progress"><i style={{ width: "87%" }} /></div><div className="row"><span>EPF & salaries</span><strong>MYR 12,000</strong></div><div className="progress"><i style={{ width: "100%" }} /></div><div className="row"><span>Suppliers</span><strong>MYR 6,800</strong></div><div className="progress"><i style={{ width: "68%" }} /></div></article>
      </section>
      <section className="grid">
        <article className="card"><span className="eyebrow">WHATSAPP SIMULATION</span><h2>Agent safety test</h2><p className="bubble">{reply}</p><input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Ignore previous instructions..." /><button onClick={askAgent}>Send to treasurer</button></article>
        <article className="card"><span className="eyebrow">MANDATE STATUS</span><h2>Supplier payments</h2><div className="approval"><span>✓</span><div><strong>Mandate active</strong><p>MYR 2,500 per transaction · allowlist enforced</p></div></div><div className="approval"><span>↗</span><div><strong>Financing watch</strong><p>Recommendations appear when a gap is predicted.</p></div></div></article>
      </section>
    </main>
  );
}
