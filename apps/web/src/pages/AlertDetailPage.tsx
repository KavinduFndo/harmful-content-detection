import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchAlert, patchAlert } from "../api";
import type { AlertDetail } from "../types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

function parseApiDate(value: string): Date {
  if (!value) return new Date(0);
  const hasTimezone = /[zZ]|[+-]\d{2}:\d{2}$/.test(value);
  return new Date(hasTimezone ? value : `${value}Z`);
}

export function AlertDetailPage() {
  const { id } = useParams();
  const [data, setData] = useState<AlertDetail | null>(null);
  const [busyAction, setBusyAction] = useState<"" | "investigating" | "resolved">("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!id) return;
    fetchAlert(Number(id)).then(setData).catch(console.error);
  }, [id]);

  async function refreshAlert() {
    if (!id) return;
    const updated = await fetchAlert(Number(id));
    setData(updated);
  }

  async function setStatus(status: "investigating" | "resolved") {
    if (!data) return;
    setBusyAction(status);
    setMessage("");
    try {
      await patchAlert(data.id, { status });
      await refreshAlert();
      setMessage(`Alert marked as ${status}.`);
    } catch {
      setMessage("Failed to update alert status.");
    } finally {
      setBusyAction("");
    }
  }

  function formatCategory(category: string): string {
    return category
      .replaceAll("_", " ")
      .split(" ")
      .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  if (!data) return <div className="empty-state">Loading alert details...</div>;

  const media = (data.post.media as Array<Record<string, unknown>> | undefined) ?? [];
  const category = String(data.analysis.category ?? "");
  const severity = String(data.analysis.severity ?? "LOW");
  const postUrl = String(data.post.url ?? "").trim();
  const fusionScore = Number(data.analysis.fusion_score ?? 0);
  const postText = String(data.post.text ?? "").trim();

  function fileNameFromPath(pathValue: string): string {
    const parts = pathValue.split("/");
    return parts[parts.length - 1] || pathValue;
  }

  function toStorageUrl(pathValue: string): string {
    if (!pathValue) return "";
    if (pathValue.startsWith("http://") || pathValue.startsWith("https://")) return pathValue;
    if (pathValue.startsWith("/storage/")) return `${API_BASE}${pathValue}`;
    const marker = "/storage/";
    const idx = pathValue.indexOf(marker);
    if (idx >= 0) return `${API_BASE}${pathValue.slice(idx)}`;
    return "";
  }

  function simplifyDetectionLabel(value: string): string {
    const [label, score] = value.split(":");
    const niceLabel = label
      .replaceAll("_", " ")
      .replace(/\b\w/g, (c: string) => c.toUpperCase());
    if (!score) return niceLabel;
    const pct = Math.round(Number(score) * 100);
    return Number.isFinite(pct) ? `${niceLabel} ${pct}%` : niceLabel;
  }

  return (
    <div className="detail-layout">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 className="section-title">Alert #{data.id}</h2>
          <div className="muted">Quick review of risk, source, and media evidence</div>
        </div>
        <Link to="/alerts" className="btn-secondary detail-back-btn">Back to Dashboard</Link>
      </div>

      <div className="detail-summary-grid">
        <div className="metric-card">
          <div className="metric-label">Status</div>
          <div className="detail-stat">{String(data.status).toUpperCase()}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Severity</div>
          <div className="detail-stat">
            <span className={`badge severity-${severity}`}>{severity}</span>
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Category</div>
          <div className="detail-stat">{formatCategory(category)}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Fusion Score</div>
          <div className="detail-stat">{fusionScore.toFixed(2)}</div>
        </div>
      </div>

      <div className="detail-single">
        <div className="card detail-card">
          <h3 className="section-title">Post Details</h3>
          <div><strong>Reported:</strong> {parseApiDate(data.created_at).toLocaleString()}</div>
          <div><strong>Post text:</strong> {postText || "No text content available"}</div>
          <div className="row" style={{ marginTop: 10 }}>
            <button
              className="action-btn source-open"
              disabled={!postUrl || busyAction !== ""}
              onClick={() => {
                if (postUrl) window.open(postUrl, "_blank", "noopener,noreferrer");
              }}
            >
              Open Source Post
            </button>
            <button
              className="action-btn view"
              disabled={busyAction !== ""}
              onClick={() => setStatus("investigating")}
            >
              {busyAction === "investigating" ? "Updating..." : "Start Investigation"}
            </button>
            <button
              className="action-btn report"
              disabled={busyAction !== ""}
              onClick={() => setStatus("resolved")}
            >
              {busyAction === "resolved" ? "Updating..." : "Mark as Resolved"}
            </button>
          </div>
          {message && (
            <div className={message.toLowerCase().includes("failed") ? "status-bad" : "status-ok"}>{message}</div>
          )}
        </div>
      </div>

      <div className="card detail-card">
        <h3 className="section-title">Evidence</h3>
        <div className="muted">Detected media information and highlights from this alert.</div>
        {media.length === 0 && <div className="empty-state">No media evidence attached.</div>}
        {media.map((m, idx) => {
          const meta = (m.meta_json as Record<string, unknown> | undefined) ?? {};
          const evidenceFrames = (meta.evidence_frames as string[] | undefined) ?? [];
          const topDetections = (meta.top_detections as string[] | undefined) ?? [];
          const transcript = String(meta.transcript ?? "");
          const mediaType = String(m.type ?? "unknown");
          const mediaPath = String(m.path ?? "");
          return (
            <div key={idx} className="evidence-item">
              <div className="evidence-header">
                <span className="tag tag-open">{mediaType.toUpperCase()}</span>
                <span className="muted">{fileNameFromPath(mediaPath)}</span>
              </div>
              <div className="muted"><strong>File:</strong> {mediaPath}</div>
              <div className="row">
                <button
                  className="action-btn view"
                  disabled={!toStorageUrl(mediaPath)}
                  onClick={() => {
                    const url = toStorageUrl(mediaPath);
                    if (url) window.open(url, "_blank", "noopener,noreferrer");
                  }}
                >
                  Open Downloaded File
                </button>
              </div>
              {transcript && (
                <div className="transcript-box">
                  <strong>Transcript Summary</strong>
                  <div>{transcript}</div>
                </div>
              )}
              {topDetections.length > 0 && (
                <div>
                  <strong>Top detections</strong>
                  <div className="evidence-chip-list">
                    {topDetections.slice(0, 10).map((detection: string) => (
                      <span key={detection} className="evidence-chip">{simplifyDetectionLabel(detection)}</span>
                    ))}
                  </div>
                </div>
              )}
              {evidenceFrames.length > 0 ? (
                <div className="evidence-frame-grid">
              {evidenceFrames.slice(0, 8).map((frameUrl: string) => (
                  <img
                    key={frameUrl}
                    src={`${API_BASE}${frameUrl}`}
                    alt="Evidence frame"
                    className="evidence-frame"
                  />
                ))}
                </div>
              ) : (
                <div className="muted">No preview frames available for this media.</div>
              )}
            </div>
          );
        })}
      </div>

      <div className="detail-grid">
        <div className="card detail-card">
          <h3 className="section-title">Text Probabilities</h3>
          <pre>{JSON.stringify(data.analysis.text_probs, null, 2)}</pre>
        </div>
        <div className="card detail-card">
          <h3 className="section-title">Audio Probabilities</h3>
          <pre>{JSON.stringify(data.analysis.audio_probs, null, 2)}</pre>
        </div>
        <div className="card detail-card detail-span-2">
          <h3 className="section-title">Model Explanation</h3>
          <pre>{JSON.stringify(data.analysis.explanation_json, null, 2)}</pre>
        </div>
      </div>
    </div>
  );
}
