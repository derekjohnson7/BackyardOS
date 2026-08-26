import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";


const METRICS = [
  {
    key: "temperature_c",
    label: "Temp",
    unit: "°F",
    color: "var(--ember)",
    digits: 1,
    transform: (value) => (value * 9) / 5 + 32,
    domain: [40, 120],
  },
  {
    key: "humidity_pct",
    label: "Humidity",
    unit: "%",
    color: "var(--dew)",
    digits: 1,
    domain: [0, 100],
  },
  {
    key: "pressure_hpa",
    label: "Pressure",
    unit: "hPa",
    color: "var(--mist)",
    digits: 1,
    domain: [980, 1040],
  },
  {
    key: "soil_moisture_pct",
    label: "Soil",
    unit: "%",
    color: "var(--bloom)",
    digits: 1,
    domain: [0, 100],
  },
];

const TIME_RANGES = [
  { key: "6h", label: "6H", hours: 6 },
  { key: "24h", label: "24H", hours: 24 },
  { key: "7d", label: "7D", hours: 24 * 7 },
];

function parseTimestamp(ts) {
  if (!ts) return null;

  const hasTimezone =
    ts.endsWith("Z") ||
    /[+-]\d{2}:\d{2}$/.test(ts);

  const normalized = hasTimezone ? ts : `${ts}Z`;

  const d = new Date(normalized);

  return isNaN(d.getTime()) ? null : d;
}

function getSoilStatus(pct) {
  if (pct == null || Number.isNaN(pct)) {
    return { label: "NO DATA", className: "no-data" };
  }
  if (pct < 30) {
    return { label: "DRY", className: "dry" };
  }
  if (pct < 65) {
    return { label: "HEALTHY", className: "healthy" };
  }
  if (pct < 85) {
    return { label: "WET", className: "wet" };
  }
  return { label: "SATURATED", className: "saturated" };
}

function fmtTime(ts) {
  const d = parseTimestamp(ts);

  if (!d) return ts;

  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function timeAgo(ts) {
  const d = parseTimestamp(ts);

  if (!d) return "";
  const diffMs = Date.now() - d.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function getNodeStatus(ts) {
  const d = parseTimestamp(ts);

  if (!d) {
    return { label: "NO DATA", className: "offline" };
  }
  const ageMinutes = (Date.now() - d.getTime()) / 60000;
  if (ageMinutes < 20) {
    return { label: "LIVE", className: "live" };
  }
  if (ageMinutes < 60) {
    return { label: "STALE", className: "stale" };
  }
  return { label: "OFFLINE", className: "offline" };
}

function groupByDevice(rows) {
  const map = new Map();
  for (const row of rows) {
    if (!map.has(row.device_id)) map.set(row.device_id, []);
    map.get(row.device_id).push(row);
  }
  for (const arr of map.values()) arr.sort(
  (a, b) => parseTimestamp(a.timestamp) - parseTimestamp(b.timestamp)
    );
  return map;
}

function useMediaQuery(query) {
  const [matches, setMatches] = useState(
    typeof window !== "undefined" ? window.matchMedia(query).matches : false
  );
  useEffect(() => {
    const mql = window.matchMedia(query);
    const handler = (e) => setMatches(e.matches);
    mql.addEventListener("change", handler);
    setMatches(mql.matches);
    return () => mql.removeEventListener("change", handler);
  }, [query]);
  return matches;
}

// ---------------------------------------------------------------------------
// Dew Ring — signature element. A circular arc gauge that reads like a bead
// of condensation collecting on greenhouse glass, filling clockwise with
// soil moisture. Replaces a generic linear progress bar.
// ---------------------------------------------------------------------------
function DewRing({ pct, size = 96 }) {
  const clamped = Math.max(0, Math.min(100, pct ?? 0));
  const r = (size - 12) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (clamped / 100) * c;
  const cx = size / 2;
  const cy = size / 2;
  return (
    <div className="dew-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <defs>
          <linearGradient id="dewGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--bloom)" />
            <stop offset="100%" stopColor="var(--dew)" />
          </linearGradient>
        </defs>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--glass-line)" strokeWidth="7" />
        <circle
          cx={cx}
          cy={cy}
          r={r}
          fill="none"
          stroke="url(#dewGrad)"
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${cx} ${cy})`}
          style={{ transition: "stroke-dashoffset 0.6s ease" }}
        />
        <circle cx={cx + r * Math.sin((clamped / 100) * 2 * Math.PI)} cy={cy - r * Math.cos((clamped / 100) * 2 * Math.PI)} r="4.5" fill="var(--dew)" opacity={clamped > 0 ? 1 : 0} />
      </svg>
      <div className="dew-ring-center">
        <span className="dew-ring-value">{clamped.toFixed(0)}</span>
        <span className="dew-ring-unit">% soil</span>
      </div>
    </div>
  );
}

function StationCard({ deviceId, index, readings, activeMetric, onMetricChange }) {
  const latest = readings[readings.length - 1];
  const [timeRange, setTimeRange] = useState("24h");
  const soilStatus = latest
  ? getSoilStatus(latest.soil_moisture_pct)
  : { label: "NO DATA", className: "no-data" };
  const nodeStatus = latest
  ? getNodeStatus(latest.timestamp)
  : { label: "NO DATA", className: "offline" };
  const metric = METRICS.find((m) => m.key === activeMetric) || METRICS[0];

  const chartData = useMemo(() => {
  const selectedRange =
    TIME_RANGES.find((range) => range.key === timeRange) || TIME_RANGES[1];

  const cutoff =
    Date.now() - selectedRange.hours * 60 * 60 * 1000;

  return readings
    .filter((r) => {
      const timestamp = parseTimestamp(r.timestamp);

      return timestamp && timestamp.getTime() >= cutoff;
    })
    .map((r) => ({
      label: fmtTime(r.timestamp),
      value:
        r[activeMetric] != null
          ? metric.transform
            ? metric.transform(r[activeMetric])
            : r[activeMetric]
          : null,
    }));
}, [readings, activeMetric, timeRange, metric]);

  return (
    <div className="station-card">
      <div className="station-head">
        <div>
          <div className="station-eyebrow">PROBE {String(index + 1).padStart(2, "0")}</div>
          <h3 className="station-id">{deviceId}</h3>
        </div>
        <div className="station-status-wrap">
          <span className={`node-status ${nodeStatus.className}`}>
            {nodeStatus.label}
          </span>

          <span className="station-sync">
            {latest ? timeAgo(latest.timestamp) : "no data"}
          </span>
        </div>
      </div>

      <div className="station-body">
       <div className="soil-summary">
        <DewRing pct={latest ? latest.soil_moisture_pct : 0} />

        <span className={`soil-status ${soilStatus.className}`}>
          {soilStatus.label}
        </span>
      </div>

        <div className="readout-grid">
          {METRICS.filter((m) => m.key !== "soil_moisture_pct").map((m) => (
            <div className="readout-chip" key={m.key}>
              <span className="readout-dot" style={{ background: m.color }} />
              <div>
                <div className="readout-label">{m.label}</div>
                <div className="readout-value">
                  {latest && latest[m.key] != null
                  ? (m.transform ? m.transform(latest[m.key]) : latest[m.key]).toFixed(m.digits)
                  : "—"}
                  <span className="readout-unit">{m.unit}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="metric-tabs">
        {METRICS.map((m) => (
          <button
            key={m.key}
            className={`metric-tab ${activeMetric === m.key ? "active" : ""}`}
            style={activeMetric === m.key ? { borderColor: m.color, color: m.color } : {}}
            onClick={() => onMetricChange(deviceId, m.key)}
          >
            {m.label}
          </button>
        ))}
      </div>
      <div className="time-range-tabs">
        {TIME_RANGES.map((range) => (
          <button
            key={range.key}
            className={`time-range-tab ${
              timeRange === range.key ? "active" : ""
            }`}
            onClick={() => setTimeRange(range.key)}
          >
            {range.label}
          </button>
        ))}
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={130}>
          <LineChart data={chartData} margin={{ top: 8, right: 12, bottom: 0, left: 10 }}>
            <CartesianGrid stroke="var(--glass-line)" strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: "var(--ink-dim)", fontSize: 9, fontFamily: "var(--font-mono)" }} tickLine={false} axisLine={{ stroke: "var(--glass-line)" }} minTickGap={40} />
            <YAxis tick={{ fill: "var(--ink-dim)", fontSize: 9, fontFamily: "var(--font-mono)" }} tickLine={false} axisLine={false} width={42} domain={metric.domain} />
            <Tooltip
              contentStyle={{ background: "var(--surface-solid)", border: "1px solid var(--glass-line)", borderRadius: 8, fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--ink)" }}
              labelStyle={{ color: "var(--ink-dim)" }}
              formatter={(v) => [`${v?.toFixed ? v.toFixed(metric.digits) : v} ${metric.unit}`, metric.label]}
            />
            <Line type="monotone" dataKey="value" stroke={metric.color} strokeWidth={2.25} dot={false} isAnimationActive animationDuration={450} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function SettingsSheet({ open, onClose, urlDraft, setUrlDraft, onConnect, autoRefresh, setAutoRefresh, status, errorMsg, lastFetched }) {
  if (!open) return null;
  return (
    <div className="sheet-overlay" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-handle" />
        <h4 className="sheet-title">Connect backend</h4>
        <form onSubmit={onConnect} className="sheet-form">
          <input
            className="sheet-input"
            placeholder="https://your-service.onrender.com/api/readings"
            value={urlDraft}
            onChange={(e) => setUrlDraft(e.target.value)}
            autoFocus
          />
          <button className="sheet-btn" type="submit">
            {status === "loading" ? "Connecting\u2026" : "Connect"}
          </button>
        </form>
        <label className="sheet-toggle">
          <span>Auto-refresh every 30s</span>
          <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
        </label>
        <div className="sheet-status">
          <span className={`status-dot ${status}`} />
          {status === "idle" && <span>not connected</span>}
          {status === "loading" && (
            <span>{errorMsg || "fetching…"}</span>
          )}
          {status === "ok" && <span>live \u00b7 synced {lastFetched ? lastFetched.toLocaleTimeString() : ""}</span>}
          {status === "error" && <span className="status-error">error: {errorMsg}</span>}
        </div>
        <button className="sheet-close" onClick={onClose}>Done</button>
      </div>
    </div>
  );
}

export default function SensorDashboard() {
  const defaultBackendUrl =
  localStorage.getItem("backyardos_backend_url") ||
  import.meta.env.VITE_API_URL ||
  "";

  const [backendUrl, setBackendUrl] = useState(defaultBackendUrl);
  const [urlDraft, setUrlDraft] = useState(defaultBackendUrl);
  
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [lastFetched, setLastFetched] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [activeMetrics, setActiveMetrics] = useState({});
  const [sheetOpen, setSheetOpen] = useState(false);
  const [activeStation, setActiveStation] = useState(0);
  const [weather, setWeather] = useState(null);
  const [weatherStatus, setWeatherStatus] = useState("idle");

  const isMobile = useMediaQuery("(max-width: 720px)");

  const fetchData = useCallback(async (url) => {
    if (!url) return;

    const maxAttempts = 3;
    const retryDelay = 10000;

    setStatus("loading");
    setErrorMsg("");

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        const res = await fetch(url);

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();

        if (!Array.isArray(data)) {
          throw new Error("Response was not a JSON array");
        }

        setRows(data);
        setStatus("ok");
        setLastFetched(new Date());

        return;
      } catch (err) {
        if (attempt === maxAttempts) {
          setStatus("error");
          setErrorMsg(err.message || "Fetch failed");
          return;
        }

        setErrorMsg(`Backend waking up... retrying (${attempt}/${maxAttempts})`);

        await new Promise((resolve) => setTimeout(resolve, retryDelay));
      }
    }
  }, []);

  const fetchWeather = useCallback(async () => {
    try {
      setWeatherStatus("loading");

      const res = await fetch("https://backyardos.onrender.com/weather");

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();

      setWeather(data);
      setWeatherStatus("ok");
    } catch (err) {
      console.error("Weather fetch failed:", err);
      setWeatherStatus("error");
    }
  }, []);

  useEffect(() => {
    if (!autoRefresh || !backendUrl) return;
    const id = setInterval(() => fetchData(backendUrl), 30000);
    return () => clearInterval(id);
  }, [autoRefresh, backendUrl, fetchData]);

  const grouped = useMemo(() => groupByDevice(rows), [rows]);
  const deviceIds = useMemo(() => Array.from(grouped.keys()).sort(), [grouped]);

  useEffect(() => {
    if (activeStation >= deviceIds.length) setActiveStation(0);
  }, [deviceIds, activeStation]);

  function handleConnect(e) {
    e.preventDefault();

    const url = urlDraft.trim();

    if (!url) return;

    localStorage.setItem("backyardos_backend_url", url);
    setBackendUrl(url);
  }

  useEffect(() => {
    if (backendUrl) {
      fetchData(backendUrl);
    }
  }, [backendUrl, fetchData]);

  function handleMetricChange(deviceId, metricKey) {
    setActiveMetrics((prev) => ({
      ...prev,
      [deviceId]: metricKey,
    }));
  }

  const visibleIds = isMobile ? (deviceIds.length ? [deviceIds[activeStation]] : []) : deviceIds;

  return (
    <div className="dash-root">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700&family=Inter:wght@400;500;600&family=Spline+Sans+Mono:wght@400;500&display=swap');

        .dash-root {
          --dusk-deep: #1b1730;
          --dusk-mid: #241f3d;
          --surface-solid: #2a2447;
          --glass: rgba(255,255,255,0.045);
          --glass-hover: rgba(255,255,255,0.075);
          --glass-line: rgba(255,255,255,0.10);
          --ink: #f2eef7;
          --ink-dim: #a89bc4;
          --bloom: #ef9fc0;
          --ember: #f4a35f;
          --dew: #6fe6da;
          --mist: #b39be0;
          --font-display: 'Bricolage Grotesque', sans-serif;
          --font-body: 'Inter', sans-serif;
          --font-mono: 'Spline Sans Mono', monospace;

          position: relative;
          background: var(--dusk-deep);
          color: var(--ink);
          font-family: var(--font-body);
          min-height: 100%;
          overflow-x: hidden;
          padding: max(18px, env(safe-area-inset-top)) 16px calc(28px + env(safe-area-inset-bottom));
          box-sizing: border-box;
        }
        .dash-root * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }

        .dash-root::before, .dash-root::after {
          content: "";
          position: absolute;
          border-radius: 50%;
          filter: blur(70px);
          z-index: 0;
          pointer-events: none;
        }
        .dash-root::before {
          width: 340px; height: 340px;
          background: radial-gradient(circle, var(--bloom) 0%, transparent 70%);
          opacity: 0.16;
          top: -120px; right: -100px;
        }
        .dash-root::after {
          width: 300px; height: 300px;
          background: radial-gradient(circle, var(--dew) 0%, transparent 70%);
          opacity: 0.14;
          bottom: 10%; left: -120px;
        }

        .dash-header, .station-grid, .sheet-overlay, .tab-bar {
          position: relative;
          z-index: 1;
        }

        .dash-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          gap: 12px;
        }
        .dash-eyebrow {
          font-family: var(--font-mono);
          font-size: 10px;
          letter-spacing: 0.16em;
          color: var(--dew);
          margin-bottom: 4px;
        }
        .dash-title {
          font-family: var(--font-display);
          font-weight: 700;
          font-size: clamp(22px, 5vw, 30px);
          margin: 0;
          letter-spacing: -0.01em;
        }
        .dash-sub {
          font-family: var(--font-mono);
          font-size: 11px;
          color: var(--ink-dim);
          margin-top: 4px;
        }
        .gear-btn {
          width: 44px; height: 44px;
          min-width: 44px;
          border-radius: 14px;
          background: var(--glass);
          border: 1px solid var(--glass-line);
          color: var(--ink);
          display: flex; align-items: center; justify-content: center;
          cursor: pointer;
          backdrop-filter: blur(10px);
        }
        .gear-btn:active { background: var(--glass-hover); }
        .gear-dot {
          position: absolute; top: 8px; right: 8px;
          width: 8px; height: 8px; border-radius: 50%;
          border: 2px solid var(--dusk-deep);
        }

        .station-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
          gap: 16px;
        }

        .station-card {
          background: var(--glass);
          border: 1px solid var(--glass-line);
          border-radius: 20px;
          padding: 20px;
          backdrop-filter: blur(14px);
        }
        .station-head {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 14px;
        }
        .station-eyebrow {
          font-family: var(--font-mono);
          font-size: 9px;
          letter-spacing: 0.14em;
          color: var(--ink-dim);
        }
        .station-id {
          font-family: var(--font-display);
          font-weight: 600;
          font-size: 18px;
          margin: 2px 0 0;
        }
        .station-sync {
          font-family: var(--font-mono);
          font-size: 10px;
          color: var(--ink-dim);
          white-space: nowrap;
          padding-top: 2px;
        }

        .station-body {
          display: flex;
          align-items: center;
          gap: 16px;
          margin-bottom: 16px;
          flex-wrap: wrap;
        }

        .dew-ring {
          position: relative;
          flex-shrink: 0;
          display: flex; align-items: center; justify-content: center;
        }
        .dew-ring-center {
          position: absolute;
          display: flex; flex-direction: column; align-items: center;
        }
        .dew-ring-value {
          font-family: var(--font-display);
          font-weight: 700;
          font-size: 22px;
          line-height: 1;
        }
        .dew-ring-unit {
          font-family: var(--font-mono);
          font-size: 8px;
          color: var(--ink-dim);
          letter-spacing: 0.06em;
          margin-top: 2px;
        }

        .readout-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 8px;
          flex: 1;
          min-width: 140px;
        }
        .readout-chip {
          display: flex;
          align-items: center;
          gap: 8px;
          background: rgba(255,255,255,0.03);
          border: 1px solid var(--glass-line);
          border-radius: 10px;
          padding: 6px 10px;
        }
        .readout-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
        .readout-label {
          font-family: var(--font-mono);
          font-size: 8px;
          letter-spacing: 0.08em;
          color: var(--ink-dim);
        }
        .readout-value {
          font-family: var(--font-mono);
          font-size: 14px;
          font-weight: 500;
        }
        .readout-unit { font-size: 10px; color: var(--ink-dim); margin-left: 2px; }

        .metric-tabs { display: flex; gap: 6px; margin-bottom: 8px; flex-wrap: wrap; }
        .metric-tab {
          background: transparent;
          border: 1px solid var(--glass-line);
          color: var(--ink-dim);
          font-family: var(--font-mono);
          font-size: 10px;
          padding: 7px 11px;
          border-radius: 8px;
          cursor: pointer;
          min-height: 32px;
        }
        .metric-tab.active { background: rgba(255,255,255,0.06); }

        .chart-wrap { margin-top: 2px; }

        .empty-state {
          font-family: var(--font-mono);
          color: var(--ink-dim);
          font-size: 13px;
          border: 1px dashed var(--glass-line);
          border-radius: 16px;
          padding: 40px;
          text-align: center;
        }

        /* Bottom tab bar — mobile only */
        .tab-bar {
          position: fixed;
          left: 12px; right: 12px; bottom: max(12px, env(safe-area-inset-bottom));
          display: none;
          gap: 6px;
          background: var(--surface-solid);
          border: 1px solid var(--glass-line);
          border-radius: 18px;
          padding: 6px;
          backdrop-filter: blur(16px);
          box-shadow: 0 10px 30px rgba(0,0,0,0.35);
        }
        .tab-btn {
          flex: 1;
          min-height: 48px;
          border-radius: 13px;
          border: none;
          background: transparent;
          color: var(--ink-dim);
          font-family: var(--font-mono);
          font-size: 10px;
          display: flex; flex-direction: column; align-items: center; justify-content: center;
          gap: 3px;
          cursor: pointer;
        }
        .tab-btn.active { background: var(--glass-hover); color: var(--ink); }
        .tab-dot { width: 6px; height: 6px; border-radius: 50%; }

        @media (max-width: 720px) {
          .tab-bar { display: flex; }
          .dash-root { padding-bottom: 96px; }
          .station-grid { grid-template-columns: 1fr; }
        }

        /* Settings sheet */
        .sheet-overlay {
          position: fixed; inset: 0;
          background: rgba(10, 8, 20, 0.6);
          display: flex; align-items: flex-end; justify-content: center;
          z-index: 50;
        }
        .sheet {
          width: 100%; max-width: 480px;
          background: var(--surface-solid);
          border: 1px solid var(--glass-line);
          border-top-left-radius: 22px; border-top-right-radius: 22px;
          padding: 10px 20px calc(20px + env(safe-area-inset-bottom));
        }
        .sheet-handle { width: 36px; height: 4px; border-radius: 2px; background: var(--glass-line); margin: 4px auto 14px; }
        .sheet-title { font-family: var(--font-display); font-weight: 600; font-size: 17px; margin: 0 0 12px; }
        .sheet-form { display: flex; gap: 8px; margin-bottom: 14px; }
        .sheet-input {
          flex: 1;
          background: rgba(255,255,255,0.05);
          border: 1px solid var(--glass-line);
          color: var(--ink);
          font-family: var(--font-mono);
          font-size: 12px;
          padding: 12px;
          border-radius: 10px;
          outline: none;
        }
        .sheet-input:focus { border-color: var(--dew); }
        .sheet-btn {
          background: var(--dew);
          color: #14202b;
          border: none;
          font-family: var(--font-mono);
          font-weight: 600;
          font-size: 12px;
          padding: 0 16px;
          border-radius: 10px;
          cursor: pointer;
        }
        .sheet-toggle {
          display: flex; justify-content: space-between; align-items: center;
          font-family: var(--font-mono); font-size: 12px; color: var(--ink-dim);
          padding: 10px 2px;
          border-top: 1px solid var(--glass-line);
        }
        .sheet-toggle input { accent-color: var(--dew); width: 18px; height: 18px; }
        .sheet-status {
          display: flex; align-items: center; gap: 8px;
          font-family: var(--font-mono); font-size: 11px; color: var(--ink-dim);
          padding: 10px 2px 4px;
        }
        .status-error { color: var(--bloom); }
        .status-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--ink-dim); display: inline-block; }
        .status-dot.ok { background: var(--dew); }
        .status-dot.error { background: var(--bloom); }
        .status-dot.loading { background: var(--ember); animation: pulse 1s infinite; }
        @keyframes pulse { 50% { opacity: 0.3; } }
        .sheet-close {
          width: 100%;
          margin-top: 14px;
          background: transparent;
          border: 1px solid var(--glass-line);
          color: var(--ink);
          font-family: var(--font-mono);
          font-size: 12px;
          padding: 12px;
          border-radius: 10px;
          cursor: pointer;
        }

        .insight-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
          margin-top: 16px;
        }

        .insight-card {
          min-height: 160px;
          background: var(--glass);
          border: 1px solid var(--glass-line);
          border-radius: 20px;
          padding: 20px;
          backdrop-filter: blur(14px);
        }

        .insight-eyebrow {
          font-family: var(--font-mono);
          font-size: 9px;
          letter-spacing: 0.14em;
          color: var(--dew);
        }

        .insight-title {
          font-family: var(--font-display);
          font-weight: 600;
          font-size: 18px;
          margin: 5px 0 12px;
        }

        .coming-soon {
          font-family: var(--font-mono);
          font-size: 11px;
          color: var(--ink-dim);
        }

        @media (max-width: 720px) {
          .insight-grid {
            grid-template-columns: 1fr;
          }
        }

        @media (prefers-reduced-motion: reduce) {
          .status-dot.loading { animation: none; }
        }

        .station-status-wrap {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .node-status {
          font-family: var(--font-mono);
          font-size: 8px;
          font-weight: 500;
          letter-spacing: 0.12em;
          padding: 4px 7px;
          border-radius: 999px;
          border: 1px solid;
        }

        .node-status.live {
          color: var(--dew);
          border-color: var(--dew);
          background: rgba(111, 230, 218, 0.08);
        }

        .node-status.stale {
          color: var(--ember);
          border-color: var(--ember);
          background: rgba(244, 163, 95, 0.08);
        }

        .node-status.offline {
          color: var(--bloom);
          border-color: var(--bloom);
          background: rgba(239, 159, 192, 0.08);
        }
        
        .soil-summary {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
        }

        .soil-status {
          font-family: var(--font-mono);
          font-size: 9px;
          font-weight: 500;
          letter-spacing: 0.12em;
          padding: 4px 8px;
          border-radius: 999px;
          border: 1px solid;
        }

        .soil-status.dry {
          color: var(--ember);
          border-color: var(--ember);
          background: rgba(244, 163, 95, 0.08);
        }

        .soil-status.healthy {
          color: var(--dew);
          border-color: var(--dew);
          background: rgba(111, 230, 218, 0.08);
        }

        .soil-status.wet {
          color: var(--mist);
          border-color: var(--mist);
          background: rgba(179, 155, 224, 0.08);
        }

        .soil-status.saturated {
          color: var(--bloom);
          border-color: var(--bloom);
          background: rgba(239, 159, 192, 0.08);
        }

        .soil-status.no-data {
          color: var(--ink-dim);
          border-color: var(--glass-line);
          background: var(--glass);
        }

        .time-range-tabs {
          display: flex;
          justify-content: flex-end;
          gap: 6px;
          margin: 10px 0 6px;
        }

        .time-range-tab {
          background: transparent;
          border: 1px solid var(--glass-line);
          color: var(--ink-dim);
          border-radius: 999px;
          padding: 4px 8px;
          font-family: var(--font-mono);
          font-size: 9px;
          cursor: pointer;
          transition: 0.2s ease;
        }

        .time-range-tab:hover {
          background: var(--glass-hover);
        }

        .time-range-tab.active {
          color: var(--dew);
          border-color: var(--dew);
          background: rgba(111, 230, 218, 0.08);
        }

        .weather-content {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }

        .weather-main {
          display: flex;
          align-items: baseline;
          gap: 12px;
        }

        .weather-temp {
          font-family: var(--font-display);
          font-size: 32px;
          font-weight: 700;
        }

        .weather-condition {
          font-family: var(--font-mono);
          font-size: 11px;
          color: var(--ink-dim);
        }

        .weather-details {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          font-family: var(--font-mono);
          font-size: 10px;
          color: var(--ink-dim);
        }
      `}</style>

      <div className="dash-header">
        <div>
          <div className="dash-eyebrow">BackyardOS</div>
          <h1 className="dash-title">Environmental Monitoring System</h1>
          <div className="dash-sub">
            {deviceIds.length
              ? `${deviceIds.length} node${deviceIds.length === 1 ? "" : "s"} reporting`
              : "not connected"}
          </div>
        </div>
        <button className="gear-btn" onClick={() => setSheetOpen(true)} aria-label="Settings">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <circle cx="12" cy="12" r="3.2" />
            <path d="M19.4 13.5a7.6 7.6 0 000-3l2-1.5-2-3.4-2.3.9a7.6 7.6 0 00-2.6-1.5L14 2.5h-4l-.5 2.5a7.6 7.6 0 00-2.6 1.5l-2.3-.9-2 3.4 2 1.5a7.6 7.6 0 000 3l-2 1.5 2 3.4 2.3-.9a7.6 7.6 0 002.6 1.5l.5 2.5h4l.5-2.5a7.6 7.6 0 002.6-1.5l2.3.9 2-3.4-2-1.5z" />
          </svg>
        </button>
      </div>

      {deviceIds.length === 0 ? (
        <div className="empty-state">
          No readings yet. Tap the gear icon to connect your backend.
        </div>
      ) : (
        <>
          <div className="station-grid">
            {visibleIds.map((id) => {
              const i = deviceIds.indexOf(id);

              return (
                <StationCard
                  key={id}
                  deviceId={id}
                  index={i}
                  readings={grouped.get(id)}
                  activeMetric={activeMetrics[id] || "soil_moisture_pct"}
                  onMetricChange={handleMetricChange}
                />
              );
            })}
          </div>

            <div className="insight-card">
              <div className="insight-eyebrow">WEATHER</div>
              <h3 className="insight-title">Local Forecast</h3>

              {weatherStatus === "loading" && (
                <div className="coming-soon">Loading weather…</div>
              )}

              {weatherStatus === "error" && (
                <div className="coming-soon">Weather unavailable</div>
              )}

              {weather && weatherStatus === "ok" && (
                <div className="weather-content">
                  <div className="weather-main">
                    <span className="weather-temp">
                      {weather.temperature_f.toFixed(0)}°F
                    </span>

                    <span className="weather-condition">
                      {weather.condition}
                    </span>
                  </div>

                  <div className="weather-details">
                    <span>Humidity {weather.humidity_pct}%</span>
                    <span>Wind {weather.wind_speed_mph} mph</span>
                    <span>Rain {weather.precipitation_in} in</span>
                  </div>
                </div>
              )}
            </div>

            <div className="insight-card">
              <div className="insight-eyebrow">VISION</div>
              <h3 className="insight-title">Plant Health</h3>
              <div className="coming-soon">
                Camera monitoring planned
              </div>
            </div>
          </div>
        </>
      )}

      {deviceIds.length > 0 && (
        <div className="tab-bar">
          {deviceIds.map((id, i) => (
            <button
              key={id}
              className={`tab-btn ${activeStation === i ? "active" : ""}`}
              onClick={() => setActiveStation(i)}
            >
              <span className="tab-dot" style={{ background: activeStation === i ? "var(--dew)" : "var(--ink-dim)" }} />
              PROBE {String(i + 1).padStart(2, "0")}
            </button>
          ))}
        </div>
      )}

      <SettingsSheet
        open={sheetOpen}
        onClose={() => setSheetOpen(false)}
        urlDraft={urlDraft}
        setUrlDraft={setUrlDraft}
        onConnect={handleConnect}
        autoRefresh={autoRefresh}
        setAutoRefresh={setAutoRefresh}
        status={status}
        errorMsg={errorMsg}
        lastFetched={lastFetched}
      />
    </div>
  );
}