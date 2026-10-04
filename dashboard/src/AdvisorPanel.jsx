
import { useEffect, useState } from "react";
import "./AdvisorPanel.css";

const trendStyles = {
  consistently_decreasing: { arrow: "↓", label: "Declining", tone: "declining" },
  consistently_increasing: { arrow: "↑", label: "Rising", tone: "rising" },
  mixed: { arrow: "↕", label: "Mixed", tone: "neutral" },
  unchanged: { arrow: "→", label: "Unchanged", tone: "neutral" },
  insufficient_data: { arrow: "—", label: "Limited data", tone: "neutral" },
};

function StatChip({ label, value, title }) {
  return (
    <div className="weather-stat" title={title}>
      <span className="weather-stat-label">{label}</span>
      <span className="weather-stat-value">{value ?? "Not available"}</span>
    </div>
  );
}

function NodeFindings({ device, findings }) {
  const trend = findings.find((finding) => finding.id.endsWith("-TREND"));
  const temperature = findings.find((finding) => finding.id.endsWith("-TEMP"));
  const badge = trendStyles[trend?.daily_direction] ?? trendStyles.insufficient_data;
  const change = trend?.net_change_percentage_points;
  const dailySummary = {
    consistently_decreasing: `Daily moisture averages declined across all ${trend?.daily_days_analyzed} analyzed dates.`,
    consistently_increasing: `Daily moisture averages rose across all ${trend?.daily_days_analyzed} analyzed dates.`,
    mixed: "Daily moisture averages rose and fell during the analyzed dates.",
    unchanged: "Daily moisture averages stayed unchanged during the analyzed dates.",
    insufficient_data: "There aren't enough days with readings to describe a daily moisture trend.",
  }[trend?.daily_direction] ?? "There isn't enough data to describe a daily moisture trend.";
  const changeSummary = typeof change !== "number" ? null
    : change === 0 ? "The latest reading matches the first reading in this window."
    : `The latest reading is ${Math.abs(change)} percentage points ${change > 0 ? "above" : "below"} the first reading in this window.`;

  return (
    <article className="advisor-node">
      <div className="advisor-node-summary">
        <span className="advisor-node-name">{device}</span>
        <span className={`advisor-trend advisor-trend-${badge.tone}`}>
          <span aria-hidden="true">{badge.arrow}</span> {badge.label}
        </span>
      </div>
      <p className="advisor-plain-summary">{dailySummary}</p>
      {changeSummary && <p className="advisor-plain-summary advisor-change-summary">{changeSummary}</p>}
      <details className="advisor-technical">
        <summary className="advisor-toggle">Technical details</summary>
      <div className="advisor-node-details">
        {trend && (
          <>
            <p className="advisor-section-label">DAILY MOISTURE</p>
            <div className="advisor-stat-grid">
              <StatChip label="DAYS WITH ENOUGH READINGS" value={trend.daily_days_analyzed} />
              <StatChip label="DAILY AVERAGE SPREAD" value={trend.daily_range_percentage_points == null ? "Not available" : `${trend.daily_range_percentage_points} percentage points`} />
              <StatChip label="DAILY RISES / FALLS" value={`${trend.increasing_intervals ?? "—"} / ${trend.decreasing_intervals ?? "—"}`} />
            </div>
            <p className="advisor-caption">
              {trend.daily_analysis_start && trend.daily_analysis_end
                ? `${trend.daily_analysis_start} – ${trend.daily_analysis_end} · At least ${trend.daily_coverage_min_readings} readings per qualifying date.`
                : "Not enough qualifying daily measurements to describe a trend."}
            </p>
          </>
        )}
        {temperature && (
          <>
            <p className="advisor-section-label">TEMPERATURE RELATIONSHIP</p>
            <p className="advisor-caption">Level correlation compares moisture and temperature readings. Change correlation compares how they change between successive readings. Values run from −1 to +1: negative means opposite directions, positive means the same direction, and near zero means little linear relationship. These associations do not establish a cause.</p>
            <div className="advisor-stat-grid">
              <StatChip label="LEVEL CORRELATION (r)" value={temperature.overall_correlation ?? "Insufficient data"} title="Correlation between moisture and temperature measurement levels" />
              <StatChip label="CHANGE CORRELATION (r)" value={temperature.consecutive_change_correlation ?? "Insufficient data"} title="Correlation between successive changes in moisture and temperature" />
              <StatChip label="VALID READINGS" value={temperature.valid_readings?.toLocaleString()} />
            </div>
          </>
        )}
        {findings.filter((finding) => !finding.id.endsWith("-TREND") && !finding.id.endsWith("-TEMP")).map((finding) => (
          <p className="advisor-caption" key={finding.id}>{finding.observation}</p>
        ))}
      </div>
      </details>
    </article>
  );
}

export default function AdvisorPanel({ backendUrl }) {
  const [analysis, setAnalysis] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const findingsByDevice = Object.groupBy(
    analysis?.findings ?? [],
    (finding) => finding.device,
  );

  useEffect(() => {
    if (!backendUrl) return;

    const controller = new AbortController();

    async function loadAnalysis() {
      setStatus("loading");
      setError("");
      setAnalysis(null);

      try {
        const url = new URL(backendUrl);
        url.pathname = "/advisor/analysis";
        url.search = "";
        url.searchParams.set("days", "7");

        const response = await fetch(url.toString(), {
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (!controller.signal.aborted) {
          setAnalysis(data);
          setStatus("ok");
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err.message || "Unable to load analysis");
          setStatus("error");
        }
      }
    }

    loadAnalysis();

    return () => controller.abort();
  }, [backendUrl]);

  return (
    <section style={{ padding: 0, marginTop: 8 }}>
      <p style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}>
        Historical sensor analysis · Last 7 days
      </p>

      {!backendUrl && <p>Connect to a backend to view findings.</p>}

      {status === "loading" && <p>Loading analysis...</p>}

      {status === "error" && (
        <p role="alert">Analysis unavailable: {error}</p>
      )}

      {status === "ok" && analysis && (
        <>
          <p className="advisor-reading-count">Readings analyzed: {analysis.reading_count?.toLocaleString()}</p>
          <p className="advisor-caption advisor-method-note">Moisture percentages are relative sensor estimates. A change from 70% to 52% is a drop of 18 percentage points.</p>

          {analysis.status === "insufficient_data" && (
            <p>{analysis.message || "Insufficient historical data."}</p>
          )}

          {analysis.findings?.length === 0 &&
            analysis.status !== "insufficient_data" && (
              <p>No findings available.</p>
            )}


          <div className="advisor-nodes">
            {Object.entries(findingsByDevice).map(([device, findings]) => (
              <NodeFindings key={device} device={device} findings={findings} />
            ))}
          </div>

        </>
      )}
    </section>
  );
}
