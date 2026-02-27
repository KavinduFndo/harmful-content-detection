import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchAlerts, patchAlert } from "../api";
import type { AlertSummary, Severity } from "../types";

const WS_BASE = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";
const CATEGORY_PRESETS: Array<{ id: string; label: string; patterns: RegExp[] }> = [
  { id: "all", label: "All", patterns: [] },
  { id: "harassment", label: "Harassment", patterns: [/harassment/i] },
  { id: "hate-speech", label: "Hate Speech", patterns: [/hate/i, /speech/i] },
  { id: "child-abuse", label: "Child Abuse", patterns: [/child/i, /abuse/i] },
  { id: "elder-abuse", label: "Elder Abuse", patterns: [/elder/i, /abuse/i] },
  { id: "violent-act", label: "Violent Act", patterns: [/violence/i, /violent/i, /act/i] },
  { id: "murder-threat", label: "Murder Threat", patterns: [/murder/i, /kill/i, /homicide/i, /threat/i] },
];

function parseApiDate(value: string): Date {
  if (!value) return new Date(0);
  const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}

export function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [q, setQ] = useState("");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [actionMsg, setActionMsg] = useState("");
  const [busyAlertId, setBusyAlertId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadAlerts() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchAlerts("new");
      setAlerts(data);
    } catch {
      setError("Failed to load alerts.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAlerts();
  }, []);

  useEffect(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/alerts`);
    ws.onmessage = (event) => {
      const incoming = JSON.parse(event.data) as AlertSummary;
      if (String(incoming.status).toLowerCase() !== "new") return;
      setAlerts((prev) => [incoming, ...prev.filter((p) => p.id !== incoming.id)]);
    };
    ws.onopen = () => ws.send("subscribed");
    return () => ws.close();
  }, []);

  function shortCategoryLabel(category: string): string {
    return category
      .replaceAll("_", " ")
      .split(" ")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  function contentSnippet(alert: AlertSummary): string {
    const label = shortCategoryLabel(alert.category);
    return `Detected ${label.toLowerCase()} content`;
  }

  function scorePercent(alert: AlertSummary): number {
    return Math.max(1, Math.min(99, Math.round(alert.fusion_score)));
  }

  function timeAgo(value: string): string {
    const deltaSec = Math.max(0, Math.floor((Date.now() - parseApiDate(value).getTime()) / 1000));
    if (deltaSec < 60) return `${deltaSec}s ago`;
    const mins = Math.floor(deltaSec / 60);
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  }

  function isRecentAlert(value: string, maxAgeHours = 24): boolean {
    const ageMs = Date.now() - parseApiDate(value).getTime();
    return ageMs >= 0 && ageMs <= maxAgeHours * 60 * 60 * 1000;
  }

  function statusTagClass(status: string): string {
    const normalized = status.toLowerCase();
    if (normalized.includes("resolved")) return "tag tag-resolved";
    if (normalized.includes("investigating")) return "tag tag-investigating";
    return "tag tag-open";
  }

  async function reportToAuthorize(alert: AlertSummary) {
    setActionMsg("");
    setBusyAlertId(alert.id);
    try {
      await patchAlert(alert.id, { status: "investigating" });
      setAlerts((prev) => prev.filter((item) => item.id !== alert.id));
      setActionMsg(`Alert #${alert.id} marked for authority review.`);
    } catch {
      setActionMsg(`Failed to report alert #${alert.id}.`);
    } finally {
      setBusyAlertId(null);
    }
  }

  const filtered = useMemo(() => {
    const selected = CATEGORY_PRESETS.find((item) => item.id === selectedCategory) ?? CATEGORY_PRESETS[0];
    return alerts.filter((a) => {
      const qMatch = q ? JSON.stringify(a).toLowerCase().includes(q.toLowerCase()) : true;
      const sMatch = severity ? a.severity === severity : true;
      const normalizedCategory = a.category.replaceAll("_", " ");
      const cMatch =
        selected.id === "all"
          ? true
          : selected.patterns.some((pattern) => pattern.test(a.category) || pattern.test(normalizedCategory));
      return qMatch && sMatch && cMatch;
    });
  }, [alerts, q, severity, selectedCategory]);

  const criticalAlerts = useMemo(
    () => filtered.filter((a) => a.severity === "CRITICAL" || a.severity === "HIGH"),
    [filtered],
  );
  const feedAlerts = useMemo(
    () => filtered.filter((a) => a.severity !== "CRITICAL" && a.severity !== "HIGH"),
    [filtered],
  );

  const scannedToday = alerts.length;
  const flaggedHarmful = alerts.filter((a) => a.severity === "CRITICAL" || a.severity === "HIGH").length;
  const reportedCases = alerts.filter((a) => a.status.toLowerCase() !== "new").length;
  const avgResponse = alerts.length
    ? `${(alerts.reduce((sum, a) => sum + a.fusion_score, 0) / alerts.length).toFixed(1)}`
    : "0.0";

  return (
    <div className="dashboard-layout">
      <div className="stats-grid">
        <div className="metric-card">
          <div className="metric-label">Scanned Today</div>
          <div className="metric-value">{scannedToday.toLocaleString()}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Flagged Harmful</div>
          <div className="metric-value">{flaggedHarmful.toLocaleString()}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Reported Cases</div>
          <div className="metric-value">{reportedCases.toLocaleString()}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Avg Response Time</div>
          <div className="metric-value">{avgResponse}m</div>
        </div>
      </div>

      <div>
        <div className="section-title">Categories</div>
        <div className="category-tabs">
          {CATEGORY_PRESETS.map((category) => (
            <button
              key={category.id}
              className={`category-btn${selectedCategory === category.id ? " active" : ""}`}
              onClick={() => setSelectedCategory(category.id)}
            >
              {category.label}
            </button>
          ))}
        </div>
      </div>

      <div className="row">
        <input placeholder="Search alerts..." value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={severity} onChange={(e) => setSeverity(e.target.value as Severity | "")}>
          <option value="">All severities</option>
          <option value="LOW">LOW</option>
          <option value="MED">MED</option>
          <option value="HIGH">HIGH</option>
          <option value="CRITICAL">CRITICAL</option>
        </select>
        <button className="btn-secondary" onClick={loadAlerts}>Refresh</button>
      </div>

      {error && <div className="status-bad">{error}</div>}
      {actionMsg && <div className="status-ok">{actionMsg}</div>}

      <div className="feed-grid">
        <div>
          <h3 className="section-title">Critical Alerts</h3>
          <div className="feed-list">
            {(loading ? [] : criticalAlerts).map((alert) => (
              <div key={alert.id} className="feed-card critical">
                <div className="feed-head">
                  <span className={`tag ${alert.severity === "CRITICAL" ? "tag-critical" : "tag-high"}`}>
                    {alert.severity}
                  </span>
                  <span className="muted">{timeAgo(alert.created_at)}</span>
                </div>
                <div className="feed-title">{contentSnippet(alert)}</div>
                <div className="feed-sub">{shortCategoryLabel(alert.category)} {scorePercent(alert)}%</div>
                <div className="feed-actions">
                  <Link className="action-btn view" to={`/alerts/${alert.id}`}>View</Link>
                  <button
                    className="action-btn report"
                    disabled={busyAlertId === alert.id}
                    onClick={() => reportToAuthorize(alert)}
                  >
                    {busyAlertId === alert.id ? "Reporting..." : "Report to Authorize"}
                  </button>
                </div>
              </div>
            ))}
            {!loading && criticalAlerts.length === 0 && <div className="empty-state">No critical alerts.</div>}
          </div>
        </div>

        <div>
          <h3 className="section-title">Content Feed</h3>
          <div className="feed-list">
            {(loading ? [] : feedAlerts).map((alert) => (
              <div key={alert.id} className="feed-card">
                <div className="feed-head">
                  {isRecentAlert(alert.created_at) ? (
                    <span className="tag tag-new">NEW</span>
                  ) : (
                    <span className={statusTagClass(String(alert.status || "OPEN"))}>
                      {String(alert.status || "OPEN").toUpperCase()}
                    </span>
                  )}
                  <span className="muted">{timeAgo(alert.created_at)}</span>
                </div>
                <div className="feed-title">{contentSnippet(alert)}</div>
                <div className="feed-sub">{shortCategoryLabel(alert.category)} {scorePercent(alert)}%</div>
                <div className="feed-actions">
                  <Link className="action-btn view" to={`/alerts/${alert.id}`}>View</Link>
                  <button
                    className="action-btn report"
                    disabled={busyAlertId === alert.id}
                    onClick={() => reportToAuthorize(alert)}
                  >
                    {busyAlertId === alert.id ? "Reporting..." : "Report to Authorize"}
                  </button>
                </div>
              </div>
            ))}
            {!loading && feedAlerts.length === 0 && <div className="empty-state">No feed items.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
