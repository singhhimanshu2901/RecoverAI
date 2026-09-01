import React, { useState, useEffect, useCallback } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell,
} from "recharts";
import {
  Activity, IndianRupee, TrendingUp, Clock, ShieldAlert, ListChecks,
  ScrollText, RefreshCw, ChevronRight, AlertTriangle, CheckCircle2,
  XCircle, PauseCircle, Search, BarChart3, Cpu, Zap,
} from "lucide-react";

const API = "https://recoverai-soqt.onrender.com";

const INK = "#0B0F14";
const SURFACE = "#131920";
const SURFACE_2 = "#1A2129";
const BORDER = "#232B35";
const TEXT = "#E8EDF2";
const MUTED = "#7C8A99";
const EMERALD = "#34D399";
const RED = "#F87171";
const BLUE = "#60A5FA";
const AMBER = "#FBBF24";
const MONO = "'IBM Plex Mono', 'JetBrains Mono', monospace";

const STATUS_STYLE = {
  OPEN: { color: MUTED, bg: "rgba(124,138,153,0.12)", icon: Activity, label: "Open" },
  ACTION_TAKEN: { color: BLUE, bg: "rgba(96,165,250,0.12)", icon: RefreshCw, label: "Action taken" },
  RECOVERED: { color: EMERALD, bg: "rgba(52,211,153,0.12)", icon: CheckCircle2, label: "Recovered" },
  STOPPED: { color: MUTED, bg: "rgba(124,138,153,0.12)", icon: XCircle, label: "Stopped" },
  ESCALATED: { color: AMBER, bg: "rgba(251,191,36,0.12)", icon: ShieldAlert, label: "Escalated" },
  VERIFY_PENDING: { color: AMBER, bg: "rgba(251,191,36,0.12)", icon: PauseCircle, label: "Verify pending" },
};

function fmtINR(n) {
  if (n === null || n === undefined) return "—";
  return "\u20B9" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
}
function fmtPct(n) {
  if (n === null || n === undefined) return "—";
  return (n * 100).toFixed(1) + "%";
}
function fmtMinutes(n) {
  if (n === null || n === undefined) return "—";
  if (n < 60) return Math.round(n) + "m";
  const h = Math.floor(n / 60);
  const m = Math.round(n % 60);
  return h + "h " + m + "m";
}
function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso + "Z")) / 1000;
  if (diff < 60) return Math.round(diff) + "s ago";
  if (diff < 3600) return Math.round(diff / 60) + "m ago";
  if (diff < 86400) return Math.round(diff / 3600) + "h ago";
  return Math.round(diff / 86400) + "d ago";
}

async function apiGet(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error("Request failed: " + path);
  return res.json();
}

function MetricCard({ label, value, sub, icon: Icon, accent }) {
  return (
    <div style={{
      background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10,
      padding: "16px 18px", display: "flex", flexDirection: "column", gap: 8, minWidth: 0,
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: 12, color: MUTED, letterSpacing: 0.3, textTransform: "uppercase" }}>{label}</span>
        {Icon && <Icon size={15} color={accent || MUTED} strokeWidth={1.75} />}
      </div>
      <span style={{ fontFamily: MONO, fontSize: 24, fontWeight: 600, color: accent || TEXT, lineHeight: 1 }}>
        {value}
      </span>
      {sub && <span style={{ fontSize: 12, color: MUTED }}>{sub}</span>}
    </div>
  );
}

function StatusBadge({ status }) {
  const s = STATUS_STYLE[status] || STATUS_STYLE.OPEN;
  const Icon = s.icon;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5, padding: "3px 9px",
      borderRadius: 20, background: s.bg, color: s.color, fontSize: 11.5, fontWeight: 600,
      letterSpacing: 0.2, whiteSpace: "nowrap",
    }}>
      <Icon size={11} strokeWidth={2} /> {s.label}
    </span>
  );
}

function PulseHeader({ metrics, loading }) {
  const recovered = metrics?.revenue_recovered_total ?? 0;
  const atRisk = metrics?.revenue_at_risk ?? 0;
  const pct = atRisk > 0 ? Math.min(100, (recovered / atRisk) * 100) : 0;

  return (
    <div style={{
      background: `linear-gradient(180deg, ${SURFACE} 0%, ${INK} 100%)`,
      border: `1px solid ${BORDER}`, borderRadius: 12, padding: "22px 24px", marginBottom: 20,
      position: "relative", overflow: "hidden",
    }}>
      <svg width="100%" height="46" viewBox="0 0 600 46" preserveAspectRatio="none"
        style={{ position: "absolute", top: 0, left: 0, opacity: 0.35 }}>
        <polyline
          points="0,23 40,23 55,8 70,38 85,23 140,23 155,12 165,34 175,23 260,23 275,6 290,40 305,23 400,23 415,15 428,31 440,23 600,23"
          fill="none" stroke={EMERALD} strokeWidth="1.5"
        />
      </svg>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: 16, position: "relative" }}>
        <div>
          <div style={{ fontSize: 12, color: MUTED, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 6 }}>
            RecoverAI — live recovery pulse
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
            <span style={{ fontFamily: MONO, fontSize: 40, fontWeight: 700, color: EMERALD, lineHeight: 1 }}>
              {loading ? "—" : fmtINR(recovered)}
            </span>
            <span style={{ fontSize: 14, color: MUTED }}>recovered of {fmtINR(atRisk)} at risk</span>
          </div>
        </div>
        <div style={{ minWidth: 160 }}>
          <div style={{ height: 6, background: SURFACE_2, borderRadius: 3, overflow: "hidden" }}>
            <div style={{ height: "100%", width: pct + "%", background: EMERALD, borderRadius: 3, transition: "width 0.6s ease" }} />
          </div>
          <div style={{ fontSize: 11, color: MUTED, marginTop: 6, textAlign: "right" }}>{pct.toFixed(1)}% of at-risk revenue recovered</div>
        </div>
      </div>
    </div>
  );
}

function OverviewScreen({ metrics }) {
  if (!metrics) return null;
  const cohortData = [
    { name: "Baseline", value: metrics.baseline_recovered },
    { name: "RecoverAI", value: metrics.ai_recovered },
  ];
  const statusPie = [
    { name: "Recovered", value: Math.round((metrics.recovery_rate || 0) * 100), color: EMERALD },
    { name: "Not recovered", value: 100 - Math.round((metrics.recovery_rate || 0) * 100), color: BORDER },
  ];

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 20 }}>
        <MetricCard label="Revenue at risk" value={fmtINR(metrics.revenue_at_risk)} icon={ShieldAlert} accent={RED} />
        <MetricCard label="Revenue recovered" value={fmtINR(metrics.revenue_recovered_total)} icon={IndianRupee} accent={EMERALD} />
        <MetricCard label="Recovery rate" value={fmtPct(metrics.recovery_rate)} icon={TrendingUp} accent={BLUE} />
        <MetricCard label="Incremental recovery" value={fmtINR(metrics.incremental_recovery)} sub="vs baseline cohort" icon={TrendingUp} accent={EMERALD} />
        <MetricCard label="Median time to recovery" value={fmtMinutes(metrics.median_time_to_recovery_minutes)} icon={Clock} accent={TEXT} />
        <MetricCard label="Open cases" value={metrics.open_cases} icon={Activity} accent={AMBER} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 14 }}>
        <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 18 }}>
          <div style={{ fontSize: 13, color: MUTED, marginBottom: 14 }}>Baseline vs RecoverAI — revenue recovered</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={cohortData} barSize={64}>
              <CartesianGrid strokeDasharray="3 3" stroke={BORDER} vertical={false} />
              <XAxis dataKey="name" tick={{ fill: MUTED, fontSize: 12 }} axisLine={{ stroke: BORDER }} tickLine={false} />
              <YAxis tick={{ fill: MUTED, fontSize: 11 }} axisLine={false} tickLine={false}
                tickFormatter={(v) => "\u20B9" + (v / 1000).toFixed(0) + "k"} />
              <Tooltip
                contentStyle={{ background: SURFACE_2, border: `1px solid ${BORDER}`, borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: TEXT }} formatter={(v) => fmtINR(v)} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                <Cell fill={MUTED} />
                <Cell fill={EMERALD} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 18, display: "flex", flexDirection: "column", alignItems: "center" }}>
          <div style={{ fontSize: 13, color: MUTED, marginBottom: 10, alignSelf: "flex-start" }}>Recovery rate</div>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={statusPie} dataKey="value" innerRadius={52} outerRadius={72} startAngle={90} endAngle={-270} stroke="none">
                {statusPie.map((e, i) => <Cell key={i} fill={e.color} />)}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
          <div style={{ fontFamily: MONO, fontSize: 22, fontWeight: 700, color: EMERALD, marginTop: -110 }}>
            {fmtPct(metrics.recovery_rate)}
          </div>
        </div>
      </div>
    </div>
  );
}

function CaseQueue({ cases, onSelect, loading }) {
  const [filter, setFilter] = useState("ALL");
  const [q, setQ] = useState("");
  const statuses = ["ALL", "OPEN", "ACTION_TAKEN", "RECOVERED", "ESCALATED", "VERIFY_PENDING", "STOPPED"];

  const filtered = cases.filter((c) => {
    if (filter !== "ALL" && c.status !== filter) return false;
    if (q && !c.customer_id.toLowerCase().includes(q.toLowerCase()) && !c.payment_id.toLowerCase().includes(q.toLowerCase())) return false;
    return true;
  });

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ position: "relative", flex: "0 0 220px" }}>
          <Search size={14} color={MUTED} style={{ position: "absolute", left: 10, top: 9 }} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search customer or payment ID"
            style={{
              width: "100%", background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 8,
              padding: "7px 10px 7px 30px", color: TEXT, fontSize: 12.5, outline: "none",
            }} />
        </div>
        {statuses.map((s) => (
          <button key={s} onClick={() => setFilter(s)} style={{
            background: filter === s ? SURFACE_2 : "transparent",
            border: `1px solid ${filter === s ? BORDER : "transparent"}`,
            color: filter === s ? TEXT : MUTED, fontSize: 11.5, padding: "6px 11px",
            borderRadius: 20, cursor: "pointer", fontWeight: 500,
          }}>
            {s === "ALL" ? "All" : (STATUS_STYLE[s]?.label || s)}
          </button>
        ))}
      </div>

      <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, overflow: "hidden" }}>
        <div style={{
          display: "grid", gridTemplateColumns: "1fr 0.9fr 0.9fr 0.9fr 1fr 1.1fr 0.7fr 24px",
          padding: "10px 16px", fontSize: 11, color: MUTED, textTransform: "uppercase",
          letterSpacing: 0.3, borderBottom: `1px solid ${BORDER}`,
        }}>
          <span>Customer</span><span>Amount</span><span>Score</span><span>Exp. value</span>
          <span>Action</span><span>Status</span><span>Age</span><span></span>
        </div>
        {loading && <div style={{ padding: 24, textAlign: "center", color: MUTED, fontSize: 13 }}>Loading cases…</div>}
        {!loading && filtered.length === 0 && (
          <div style={{ padding: 24, textAlign: "center", color: MUTED, fontSize: 13 }}>No cases match this filter.</div>
        )}
        {filtered.slice(0, 60).map((c) => (
          <div key={c.id} onClick={() => onSelect(c.id)} style={{
            display: "grid", gridTemplateColumns: "1fr 0.9fr 0.9fr 0.9fr 1fr 1.1fr 0.7fr 24px",
            padding: "11px 16px", fontSize: 13, borderBottom: `1px solid ${BORDER}`,
            cursor: "pointer", alignItems: "center", transition: "background 0.1s",
          }}
            onMouseEnter={(e) => e.currentTarget.style.background = SURFACE_2}
            onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}>
            <span style={{ fontFamily: MONO, fontSize: 12.5 }}>{c.customer_id}</span>
            <span style={{ fontFamily: MONO, fontSize: 12.5 }}>{fmtINR(c.amount)}</span>
            <span style={{ fontFamily: MONO, fontSize: 12.5, color: c.recovery_score > 0.6 ? EMERALD : c.recovery_score > 0.3 ? AMBER : RED }}>
              {c.recovery_score !== null ? (c.recovery_score * 100).toFixed(0) + "%" : "—"}
            </span>
            <span style={{ fontFamily: MONO, fontSize: 12.5, color: MUTED }}>{fmtINR(c.expected_value)}</span>
            <span style={{ fontSize: 12, color: BLUE }}>{c.recommended_action || "—"}</span>
            <span><StatusBadge status={c.status} /></span>
            <span style={{ fontSize: 11.5, color: MUTED }}>{timeAgo(c.created_at)}</span>
            <ChevronRight size={14} color={MUTED} />
          </div>
        ))}
      </div>
    </div>
  );
}

function CaseDetail({ caseId, onBack }) {
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    apiGet("/recovery/cases/" + caseId).then(setDetail).catch(() => setDetail(null));
  }, [caseId]);

  if (!detail) return <div style={{ padding: 24, color: MUTED, fontSize: 13 }}>Loading case…</div>;
  const c = detail.case;

  return (
    <div>
      <button onClick={onBack} style={{
        background: "transparent", border: "none", color: MUTED, fontSize: 12.5,
        cursor: "pointer", marginBottom: 14, display: "flex", alignItems: "center", gap: 4, padding: 0,
      }}>
        ← Back to queue
      </button>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
        <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 18 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
            <div>
              <div style={{ fontFamily: MONO, fontSize: 20, fontWeight: 600 }}>{fmtINR(c.amount)}</div>
              <div style={{ fontSize: 12, color: MUTED, marginTop: 2 }}>{c.customer_id} · {c.payment_id}</div>
            </div>
            <StatusBadge status={c.status} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, fontSize: 12.5 }}>
            <div><span style={{ color: MUTED }}>Failure reason</span><br />{c.failure_code}</div>
            <div><span style={{ color: MUTED }}>Priority</span><br />{c.priority}</div>
            <div><span style={{ color: MUTED }}>Attempts</span><br />{c.attempt_number}</div>
            <div><span style={{ color: MUTED }}>Created</span><br />{timeAgo(c.created_at)}</div>
          </div>
        </div>

        <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 18 }}>
          <div style={{ fontSize: 12, color: MUTED, marginBottom: 10 }}>AI recovery reasoning</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12.5, color: MUTED }}>Recovery score</span>
              <span style={{ fontFamily: MONO, fontSize: 13, color: EMERALD }}>
                {c.recovery_score !== null ? (c.recovery_score * 100).toFixed(1) + "%" : "—"}
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12.5, color: MUTED }}>Expected value</span>
              <span style={{ fontFamily: MONO, fontSize: 13 }}>{fmtINR(c.expected_value)}</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ fontSize: 12.5, color: MUTED }}>Recommended action</span>
              <span style={{ fontSize: 12.5, color: BLUE, fontWeight: 600 }}>{c.recommended_action || "—"}</span>
            </div>
            {c.recovered && (
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ fontSize: 12.5, color: MUTED }}>Recovered amount</span>
                <span style={{ fontFamily: MONO, fontSize: 13, color: EMERALD }}>{fmtINR(c.recovered_amount)}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 18 }}>
        <div style={{ fontSize: 12, color: MUTED, marginBottom: 12 }}>Audit trail</div>
        <div style={{ display: "flex", flexDirection: "column" }}>
          {detail.audit_trail.map((a, i) => (
            <div key={i} style={{
              display: "flex", gap: 12, padding: "9px 0",
              borderBottom: i < detail.audit_trail.length - 1 ? `1px solid ${BORDER}` : "none",
            }}>
              <div style={{ width: 7, height: 7, borderRadius: "50%", background: BLUE, marginTop: 5, flexShrink: 0 }} />
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 12.5, fontWeight: 600 }}>{a.event_type.replaceAll("_", " ")}</span>
                  <span style={{ fontSize: 11, color: MUTED, fontFamily: MONO }}>{timeAgo(a.timestamp)}</span>
                </div>
                <div style={{ fontSize: 11.5, color: MUTED, marginTop: 2, fontFamily: MONO }}>
                  {Object.entries(a.payload).slice(0, 4).map(([k, v]) => `${k}: ${v}`).join("  ·  ")}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AuditScreen() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet("/audit?limit=100").then((d) => { setEvents(d); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  return (
    <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 4 }}>
      {loading && <div style={{ padding: 24, textAlign: "center", color: MUTED, fontSize: 13 }}>Loading audit log…</div>}
      {!loading && events.length === 0 && (
        <div style={{ padding: 24, textAlign: "center", color: MUTED, fontSize: 13 }}>No audit events yet.</div>
      )}
      {events.map((e, i) => (
        <div key={i} style={{
          display: "flex", gap: 14, padding: "10px 16px", alignItems: "center",
          borderBottom: i < events.length - 1 ? `1px solid ${BORDER}` : "none", fontSize: 12.5,
        }}>
          <span style={{ fontFamily: MONO, fontSize: 11, color: MUTED, width: 90, flexShrink: 0 }}>{timeAgo(e.timestamp)}</span>
          <span style={{ fontWeight: 600, width: 150, flexShrink: 0 }}>{e.event_type.replaceAll("_", " ")}</span>
          <span style={{ fontFamily: MONO, fontSize: 11, color: MUTED, flex: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {e.case_id?.slice(0, 8)}… {Object.entries(e.payload || {}).slice(0, 3).map(([k, v]) => `${k}=${v}`).join(" ")}
          </span>
        </div>
      ))}
    </div>
  );
}

const TABS = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "queue", label: "Recovery queue", icon: ListChecks },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "audit", label: "Audit", icon: ScrollText },
  { id: "system", label: "System", icon: Cpu },
];

const FAILURE_LABELS = {
  RETRYABLE: "Retryable", INSUFFICIENT_FUNDS: "Insufficient funds",
  CARD_EXPIRED: "Card expired", CUSTOMER_ACTION_REQUIRED: "Customer action required",
  BANK_DECLINE: "Bank decline", UNKNOWN: "Unknown",
};

function AnalyticsScreen() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiGet("/recovery/analytics").then((d) => { setData(d); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ padding: 24, textAlign: "center", color: MUTED, fontSize: 13 }}>Loading analytics…</div>;
  if (!data) return null;

  const failureRows = Object.entries(data.by_failure_code || {})
    .sort((a, b) => b[1].total - a[1].total);
  const actionRows = Object.entries(data.by_recommended_action || {})
    .sort((a, b) => b[1].total - a[1].total);
  const actionChartData = actionRows.map(([k, v]) => ({ name: k, value: v.amount_recovered }));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 18 }}>
        <div style={{ fontSize: 13, color: MUTED, marginBottom: 14 }}>Revenue recovered by action taken</div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={actionChartData} barSize={44}>
            <CartesianGrid strokeDasharray="3 3" stroke={BORDER} vertical={false} />
            <XAxis dataKey="name" tick={{ fill: MUTED, fontSize: 11 }} axisLine={{ stroke: BORDER }} tickLine={false} />
            <YAxis tick={{ fill: MUTED, fontSize: 11 }} axisLine={false} tickLine={false}
              tickFormatter={(v) => "\u20B9" + (v / 1000).toFixed(0) + "k"} />
            <Tooltip contentStyle={{ background: SURFACE_2, border: `1px solid ${BORDER}`, borderRadius: 8, fontSize: 12 }}
              labelStyle={{ color: TEXT }} formatter={(v) => fmtINR(v)} />
            <Bar dataKey="value" fill={BLUE} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 18 }}>
          <div style={{ fontSize: 13, color: MUTED, marginBottom: 12 }}>Recovery rate by failure reason</div>
          {failureRows.map(([code, v]) => (
            <div key={code} style={{ marginBottom: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12.5, marginBottom: 5 }}>
                <span>{FAILURE_LABELS[code] || code}</span>
                <span style={{ fontFamily: MONO, color: MUTED }}>{v.recovered}/{v.total} · {fmtPct(v.recovery_rate)}</span>
              </div>
              <div style={{ height: 5, background: SURFACE_2, borderRadius: 3, overflow: "hidden" }}>
                <div style={{ height: "100%", width: (v.recovery_rate * 100) + "%", background: EMERALD, borderRadius: 3 }} />
              </div>
            </div>
          ))}
        </div>

        <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 18 }}>
          <div style={{ fontSize: 13, color: MUTED, marginBottom: 12 }}>Case status distribution</div>
          {Object.entries(data.by_status || {}).map(([status, count]) => {
            const s = STATUS_STYLE[status] || STATUS_STYLE.OPEN;
            return (
              <div key={status} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: `1px solid ${BORDER}` }}>
                <StatusBadge status={status} />
                <span style={{ fontFamily: MONO, fontSize: 13 }}>{count}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function SystemScreen() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    apiGet("/model/status").then(setStatus).catch(() => setStatus(null));
  }, []);

  if (!status) return <div style={{ padding: 24, textAlign: "center", color: MUTED, fontSize: 13 }}>Loading system status…</div>;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
      <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 18 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <Zap size={15} color={EMERALD} />
          <span style={{ fontSize: 13, color: MUTED }}>Recovery scoring engine</span>
        </div>
        <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 6 }}>
          {status.scoring_mode === "xgboost_ml_model" ? "XGBoost ML model" : "Rule-based scorer"}
        </div>
        <div style={{ fontSize: 12.5, color: MUTED, lineHeight: 1.6 }}>
          {status.scoring_mode === "xgboost_ml_model"
            ? "Trained on historical case outcomes. Falls back to the transparent rule-based scorer automatically on any inference error."
            : "No trained model found yet — using the transparent, auditable rule-based scorer. Run train_model.py once enough labeled cases exist."}
        </div>
      </div>

      <div style={{ background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 18 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
          <IndianRupee size={15} color={BLUE} />
          <span style={{ fontSize: 13, color: MUTED }}>Payment provider</span>
        </div>
        <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 6 }}>
          {status.payment_provider_mode === "live_sandbox" ? "Razorpay sandbox (live)" : "Mock mode"}
        </div>
        <div style={{ fontSize: 12.5, color: MUTED, lineHeight: 1.6 }}>
          {status.payment_provider_mode === "live_sandbox"
            ? "Connected to Razorpay test-mode credentials. Payment links are created via the real sandbox API."
            : "No Razorpay sandbox credentials configured — payment links are simulated so the full recovery loop still runs end-to-end for demos."}
        </div>
      </div>

      <div style={{ gridColumn: "1 / -1", background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 10, padding: 18 }}>
        <div style={{ fontSize: 13, color: MUTED, marginBottom: 10 }}>Policy limits (hard-coded, deterministic)</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, fontSize: 12.5 }}>
          <div><span style={{ color: MUTED }}>Max retries</span><br /><span style={{ fontFamily: MONO, fontSize: 16 }}>2</span></div>
          <div><span style={{ color: MUTED }}>Max messages</span><br /><span style={{ fontFamily: MONO, fontSize: 16 }}>2</span></div>
          <div><span style={{ color: MUTED }}>Cooldown</span><br /><span style={{ fontFamily: MONO, fontSize: 16 }}>6h</span></div>
          <div><span style={{ color: MUTED }}>Max recovery window</span><br /><span style={{ fontFamily: MONO, fontSize: 16 }}>72h</span></div>
        </div>
      </div>
    </div>
  );
}

async function apiPost(path, body) {
  const res = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error("Request failed: " + path);
  return res.json();
}

function AmountPromptModal({ onCancel, onConfirm }) {
  const [value, setValue] = useState("499");
  const num = parseFloat(value);
  const valid = !isNaN(num) && num > 0 && num <= 100000;

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex",
      alignItems: "center", justifyContent: "center", zIndex: 100, padding: 20,
    }}>
      <div style={{
        background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 14,
        padding: 28, maxWidth: 360, width: "100%",
      }}>
        <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>Live Recovery Demo</div>
        <div style={{ fontSize: 12, color: MUTED, marginBottom: 18 }}>
          Enter the amount for this real Razorpay test-mode payment link.
        </div>
        <div style={{ position: "relative", marginBottom: 6 }}>
          <span style={{ position: "absolute", left: 12, top: 11, color: MUTED, fontSize: 15, fontFamily: MONO }}>₹</span>
          <input
            type="number" min="1" max="100000" value={value}
            onChange={(e) => setValue(e.target.value)}
            autoFocus
            style={{
              width: "100%", background: SURFACE_2, border: `1px solid ${BORDER}`, borderRadius: 8,
              padding: "10px 12px 10px 26px", color: TEXT, fontSize: 16, fontFamily: MONO, outline: "none",
            }}
          />
        </div>
        {!valid && <div style={{ fontSize: 11.5, color: RED, marginBottom: 8 }}>Enter an amount between ₹1 and ₹1,00,000.</div>}
        <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
          <button onClick={onCancel} style={{
            flex: 1, background: "transparent", border: `1px solid ${BORDER}`, color: MUTED,
            borderRadius: 8, padding: "9px 0", fontSize: 12.5, cursor: "pointer",
          }}>
            Cancel
          </button>
          <button
            disabled={!valid}
            onClick={() => onConfirm(num)}
            style={{
              flex: 1, background: valid ? EMERALD : SURFACE_2, border: "none",
              color: valid ? INK : MUTED, fontWeight: 700, borderRadius: 8,
              padding: "9px 0", fontSize: 12.5, cursor: valid ? "pointer" : "not-allowed",
            }}
          >
            Generate Link
          </button>
        </div>
      </div>
    </div>
  );
}

function LiveDemoModal({ amount, onClose, onDone }) {
  const [stage, setStage] = useState("running"); // running | link_ready | polling | recovered | error
  const [caseId, setCaseId] = useState(null);
  const [link, setLink] = useState(null);
  const [errMsg, setErrMsg] = useState("");
  const pollRef = React.useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      try {
        const suffix = Date.now().toString().slice(-6);
        const created = await apiPost("/events/payment-failed", {
          payment_id: `pay_live_demo_${suffix}`,
          customer_id: `C_DEMO_${suffix}`,
          amount: amount,
          failure_code: "CUSTOMER_ACTION_REQUIRED",
          previous_success_count: 10,
          previous_failure_count: 1,
          subscription_age_days: 200,
        });
        if (cancelled) return;
        setCaseId(created.id);

        await apiPost(`/recovery/analyze?case_id=${created.id}`);
        if (cancelled) return;

        const executed = await apiPost("/recovery/execute", { case_id: created.id });
        if (cancelled) return;

        const detail = await apiGet(`/recovery/cases/${created.id}`);
        const lastExec = [...detail.audit_trail].reverse().find((a) => a.event_type === "ACTION_EXECUTED");
        const url = lastExec?.payload?.provider_result?.short_url;

        if (!url) {
          setErrMsg("No payment link was generated — case may have been escalated or stopped by policy. Try again.");
          setStage("error");
          return;
        }
        setLink(url);
        setStage("link_ready");
      } catch (e) {
        setErrMsg(e.message);
        setStage("error");
      }
    }
    run();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (stage !== "polling" && stage !== "link_ready") return;
    pollRef.current = setInterval(async () => {
      if (!caseId) return;
      try {
        const detail = await apiGet(`/recovery/cases/${caseId}`);
        if (detail.case.status === "RECOVERED") {
          setStage("recovered");
          clearInterval(pollRef.current);
          onDone();
        }
      } catch { /* ignore transient errors while polling */ }
    }, 3000);
    return () => clearInterval(pollRef.current);
  }, [stage, caseId, onDone]);

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex",
      alignItems: "center", justifyContent: "center", zIndex: 100, padding: 20,
    }}>
      <div style={{
        background: SURFACE, border: `1px solid ${BORDER}`, borderRadius: 14,
        padding: 28, maxWidth: 440, width: "100%", textAlign: "center",
      }}>
        <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>Live Recovery Demo</div>
        <div style={{ fontSize: 12, color: MUTED, marginBottom: 22 }}>Real Razorpay test-mode payment, {fmtINR(amount)}</div>

        {stage === "running" && (
          <div style={{ padding: "20px 0" }}>
            <RefreshCw size={22} color={BLUE} className="spin" />
            <div style={{ fontSize: 13, color: MUTED, marginTop: 12 }}>
              Creating case → scoring → policy check → generating payment link…
            </div>
          </div>
        )}

        {(stage === "link_ready" || stage === "polling") && (
          <div>
            <div style={{ fontSize: 12.5, color: MUTED, marginBottom: 16, lineHeight: 1.6 }}>
              Payment link generated and approved by the policy engine. Open it,
              pay with UPI ID <b style={{ color: TEXT }}>success@razorpay</b>, and this
              screen updates automatically when Razorpay's webhook confirms it.
            </div>
            <a href={link} target="_blank" rel="noreferrer" style={{
              display: "block", background: EMERALD, color: INK, fontWeight: 700,
              padding: "12px 20px", borderRadius: 8, textDecoration: "none", fontSize: 14, marginBottom: 14,
            }}>
              Open Payment Link →
            </a>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, color: AMBER, fontSize: 12 }}>
              <PauseCircle size={13} /> Waiting for real webhook confirmation…
            </div>
          </div>
        )}

        {stage === "recovered" && (
          <div style={{ padding: "10px 0" }}>
            <CheckCircle2 size={32} color={EMERALD} />
            <div style={{ fontSize: 16, fontWeight: 700, color: EMERALD, marginTop: 10 }}>Recovered — {fmtINR(amount)}</div>
            <div style={{ fontSize: 12, color: MUTED, marginTop: 4 }}>Confirmed live by Razorpay's webhook.</div>
          </div>
        )}

        {stage === "error" && (
          <div style={{ padding: "10px 0" }}>
            <AlertTriangle size={26} color={RED} />
            <div style={{ fontSize: 13, color: RED, marginTop: 10 }}>{errMsg}</div>
          </div>
        )}

        <button onClick={onClose} style={{
          marginTop: 20, background: "transparent", border: `1px solid ${BORDER}`, color: MUTED,
          borderRadius: 8, padding: "8px 16px", fontSize: 12.5, cursor: "pointer",
        }}>
          Close
        </button>
      </div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("overview");
  const [metrics, setMetrics] = useState(null);
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState(null);
  const [error, setError] = useState(null);
  const [showDemo, setShowDemo] = useState(false);
  const [demoAmount, setDemoAmount] = useState(null);

  const refresh = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([apiGet("/recovery/metrics"), apiGet("/recovery/cases?limit=100")])
      .then(([m, c]) => { setMetrics(m); setCases(c); setLoading(false); })
      .catch((e) => { setError(e.message + " — the backend may be waking up (free-tier cold start), try refresh in ~20s"); setLoading(false); });
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  return (
    <div style={{
      background: INK, minHeight: "100vh", color: TEXT,
      fontFamily: "'Inter', -apple-system, sans-serif", padding: "24px 28px",
    }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 18 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 30, height: 30, borderRadius: 7, background: EMERALD,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <Activity size={16} color={INK} strokeWidth={2.5} />
            </div>
            <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: -0.2 }}>RecoverAI</span>
            <span style={{ fontSize: 11, color: MUTED, background: SURFACE, border: `1px solid ${BORDER}`, padding: "2px 8px", borderRadius: 12 }}>
              sandbox
            </span>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button onClick={() => setShowDemo(true)} style={{
              background: EMERALD, border: "none", color: INK, borderRadius: 8,
              padding: "6px 14px", fontSize: 12.5, fontWeight: 700, cursor: "pointer",
              display: "flex", alignItems: "center", gap: 6,
            }}>
              <Zap size={13} /> Live Demo Payment
            </button>
            <button onClick={refresh} style={{
              background: SURFACE, border: `1px solid ${BORDER}`, color: MUTED, borderRadius: 8,
              padding: "6px 12px", fontSize: 12, cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
            }}>
              <RefreshCw size={12} className={loading ? "spin" : ""} /> Refresh
            </button>
          </div>
        </div>

        {showDemo && !demoAmount && (
          <AmountPromptModal
            onCancel={() => setShowDemo(false)}
            onConfirm={(amt) => setDemoAmount(amt)}
          />
        )}
        {showDemo && demoAmount && (
          <LiveDemoModal
            amount={demoAmount}
            onClose={() => { setShowDemo(false); setDemoAmount(null); }}
            onDone={refresh}
          />
        )}

        {error && (
          <div style={{
            background: "rgba(248,113,113,0.1)", border: `1px solid ${RED}`, borderRadius: 8,
            padding: "10px 14px", fontSize: 12.5, color: RED, marginBottom: 16, display: "flex", gap: 8, alignItems: "center",
          }}>
            <AlertTriangle size={14} /> {error}
          </div>
        )}

        <PulseHeader metrics={metrics} loading={loading} />

        {!selectedCase && (
          <div style={{ display: "flex", gap: 4, marginBottom: 18, borderBottom: `1px solid ${BORDER}` }}>
            {TABS.map((t) => {
              const Icon = t.icon;
              const active = tab === t.id;
              return (
                <button key={t.id} onClick={() => setTab(t.id)} style={{
                  background: "transparent", border: "none", cursor: "pointer",
                  padding: "10px 4px", marginRight: 22, display: "flex", alignItems: "center", gap: 6,
                  color: active ? TEXT : MUTED, fontSize: 13, fontWeight: 500,
                  borderBottom: active ? `2px solid ${EMERALD}` : "2px solid transparent",
                }}>
                  <Icon size={14} /> {t.label}
                </button>
              );
            })}
          </div>
        )}

        {selectedCase ? (
          <CaseDetail caseId={selectedCase} onBack={() => setSelectedCase(null)} />
        ) : (
          <>
            {tab === "overview" && <OverviewScreen metrics={metrics} />}
            {tab === "queue" && <CaseQueue cases={cases} onSelect={setSelectedCase} loading={loading} />}
            {tab === "analytics" && <AnalyticsScreen />}
            {tab === "audit" && <AuditScreen />}
            {tab === "system" && <SystemScreen />}
          </>
        )}
      </div>
      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spin { animation: spin 1s linear infinite; }
        * { box-sizing: border-box; }
        body { margin: 0; }
      `}</style>
    </div>
  );
}