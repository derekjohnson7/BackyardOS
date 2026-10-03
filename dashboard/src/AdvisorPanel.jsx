
import { useEffect, useState } from "react";

export default function AdvisorPanel({ backendUrl }) {
  const [analysis, setAnalysis] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const findingsByDevice = Object.groupBy(
  analysis?.findings ?? [],
  (finding) => finding.device
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
          <p>Readings analyzed: {analysis.reading_count}</p>

          {analysis.status === "insufficient_data" && (
            <p>{analysis.message || "Insufficient historical data."}</p>
          )}

          {analysis.findings?.length === 0 &&
            analysis.status !== "insufficient_data" && (
              <p>No findings available.</p>
            )}


{Object.entries(findingsByDevice).map(([device, findings]) => (
  <article
    key={device}
    style={{
      padding: 16,
      marginTop: 12,
      border: "1px solid #8885",
      borderRadius: 12,
    }}
  >
    <h3 style={{ marginTop: 0 }}>{device}</h3>

    {findings.map((finding) => (
      <div
        key={finding.id}
        style={{
          paddingTop: 10,
          paddingBottom: 10,
          borderTop: "1px solid #8883",
        }}
      >
        <strong style={{ fontSize: 12 }}>
          {finding.id.endsWith("-TREND")
            ? "SOIL MOISTURE"
            : "TEMPERATURE RELATIONSHIP"}
        </strong>

        <p style={{ fontSize: 12, lineHeight: 1.5 }}>
          {finding.observation}
        </p>

        {finding.id.endsWith("-TREND") ? (
          <div style={{ fontSize: 12, lineHeight: 1.7 }}>
            <div>
              <strong>Trend:</strong>{" "}
              {finding.daily_direction?.replaceAll("_", " ")}
            </div>
            <div>
              <strong>Net change:</strong>{" "}
              {finding.net_change_percentage_points} percentage points
            </div>
            <div>
              <strong>Days analyzed:</strong>{" "}
              {finding.daily_days_analyzed}
            </div>
          </div>
        ) : (
          <div style={{ fontSize: 12, lineHeight: 1.7 }}>
            <div>
              <strong>Overall correlation:</strong>{" "}
              {finding.overall_correlation ?? "Insufficient data"}
            </div>
            <div>
              <strong>Change correlation:</strong>{" "}
              {finding.consecutive_change_correlation ?? "Insufficient data"}
            </div>
            <div>
              <strong>Valid readings:</strong>{" "}
              {finding.valid_readings}
            </div>
          </div>
        )}
      </div>
    ))}
  </article>
))}

        </>
      )}
    </section>
  );
}
