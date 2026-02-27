import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchAlerts } from "../api";
import type { AlertSummary } from "../types";

function parseApiDate(value: string): Date {
  if (!value) return new Date(0);
  const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}

export function ResolvedCasesPage() {
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchAlerts("resolved");
      setAlerts(data);
    } catch {
      setError("Failed to load resolved cases.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="dashboard-layout">
      <h2 className="section-title">Resolved Cases</h2>
      <div className="row">
        <button className="btn-secondary" onClick={load}>Refresh</button>
      </div>
      {error && <div className="status-bad">{error}</div>}
      <div className="feed-list">
        {loading ? (
          <div className="empty-state">Loading resolved cases...</div>
        ) : alerts.length === 0 ? (
          <div className="empty-state">No resolved cases.</div>
        ) : (
          alerts.map((alert) => (
            <div key={alert.id} className="feed-card">
              <div className="feed-head">
                <span className="tag tag-resolved">RESOLVED</span>
                <span className="muted">{parseApiDate(alert.created_at).toLocaleString()}</span>
              </div>
              <div className="feed-title">{(alert.category ?? "").replaceAll("_", " ")}</div>
              <div className="feed-sub">Risk {Number(alert.fusion_score ?? 0).toFixed(2)} • Alert #{alert.id}</div>
              <div className="feed-actions">
                <Link className="action-btn view" to={`/alerts/${alert.id}`}>View</Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
