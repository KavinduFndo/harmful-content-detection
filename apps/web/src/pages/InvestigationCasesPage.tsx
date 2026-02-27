import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchAlerts, patchAlert } from "../api";
import type { AlertSummary } from "../types";

function parseApiDate(value: string): Date {
  if (!value) return new Date(0);
  const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}

export function InvestigationCasesPage() {
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchAlerts("investigating");
      setAlerts(data);
    } catch {
      setError("Failed to load investigation cases.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function markResolved(alertId: number) {
    setBusyId(alertId);
    try {
      await patchAlert(alertId, { status: "resolved" });
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="dashboard-layout">
      <h2 className="section-title">Investigation Cases</h2>
      <div className="row">
        <button className="btn-secondary" onClick={load}>Refresh</button>
      </div>
      {error && <div className="status-bad">{error}</div>}
      <div className="feed-list">
        {loading ? (
          <div className="empty-state">Loading investigation cases...</div>
        ) : alerts.length === 0 ? (
          <div className="empty-state">No investigation cases.</div>
        ) : (
          alerts.map((alert) => (
            <div key={alert.id} className="feed-card">
              <div className="feed-head">
                <span className="tag tag-investigating">INVESTIGATING</span>
                <span className="muted">{parseApiDate(alert.created_at).toLocaleString()}</span>
              </div>
              <div className="feed-title">{(alert.category ?? "").replaceAll("_", " ")}</div>
              <div className="feed-sub">Risk {Number(alert.fusion_score ?? 0).toFixed(2)} • Alert #{alert.id}</div>
              <div className="feed-actions">
                <Link className="action-btn view" to={`/alerts/${alert.id}`}>View</Link>
                <button
                  className="action-btn report"
                  disabled={busyId === alert.id}
                  onClick={() => markResolved(alert.id)}
                >
                  {busyId === alert.id ? "Updating..." : "Mark Resolved"}
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
