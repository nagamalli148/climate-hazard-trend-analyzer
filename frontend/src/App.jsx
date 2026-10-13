
import { useState } from "react";
import { buildAnalysisCsv } from "./export.js";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

const API_URL = "/api";

export default function App() {
  const [latitude, setLatitude] = useState("16.5062");
  const [longitude, setLongitude] = useState("80.648");
  const [startYear, setStartYear] = useState("2015");
  const [endYear, setEndYear] = useState("2020");

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [hazardType, setHazardType] = useState("heatwave");

  async function analyzeClimate() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const params = new URLSearchParams({
        latitude,
        longitude,
        start_year: startYear,
        end_year: endYear,
        hazard: hazardType,
      });

      const response = await fetch(
        `${API_URL}/analyze?${params}`
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to analyze climate data"
        );
      }

      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function exportCsv() {
    const csv = buildAnalysisCsv(result);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const hazardSlug = result.hazard.replaceAll("_", "-");

    link.href = url;
    link.download = `climate-hazard-${hazardSlug}-${result.analysis_period.start_year}-${result.analysis_period.end_year}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return (
    <main className="page">
      <h1>Climate Hazard Trend Analyzer</h1>
      <p>Explore historical climate hazard patterns for a region.</p>

      <section className="filters" style={styles.filters}>
        <label>
          Hazard type
          <select
            value={hazardType}
            onChange={(event) => {
              setHazardType(event.target.value);
              setResult(null);
            }}
          >
            <option value="heatwave">Heatwave</option>
            <option value="drought">Drought</option>
            <option value="heavy_rainfall">Heavy rainfall</option>
          </select>
        </label>

        <label>
          Latitude
          <input
            type="number"
            min="-90"
            max="90"
            step="any"
            value={latitude}
            onChange={(e) => setLatitude(e.target.value)}
          />
        </label>

        <label>
          Longitude
          <input
            type="number"
            min="-180"
            max="180"
            step="any"
            value={longitude}
            onChange={(e) => setLongitude(e.target.value)}
          />
        </label>

        <label>
          Start year
          <input
            type="number"
            value={startYear}
            onChange={(e) => setStartYear(e.target.value)}
          />
        </label>

        <label>
          End year
          <input
            type="number"
            value={endYear}
            onChange={(e) => setEndYear(e.target.value)}
          />
        </label>

        <button
          onClick={analyzeClimate}
          disabled={loading}
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </section>

      {error && (
        <p role="alert" style={styles.error}>
          {error}
        </p>
      )}

      {result && (
        <>
          <section className="report-meta" aria-label="Export report details">
            <p>
              <strong>Region:</strong> {result.location.latitude},{" "}
              {result.location.longitude}
            </p>
            <p>
              <strong>Analysis period:</strong>{" "}
              {result.analysis_period.start_year} to{" "}
              {result.analysis_period.end_year}
            </p>
          </section>

          <div className="export-actions screen-only">
            <button type="button" onClick={exportCsv}>
              Download CSV
            </button>
          </div>

          <section style={styles.cards}>
            <article style={styles.card}>
              <p>Total events</p>
              <h2>{result.total_events}</h2>
            </article>

            <article style={styles.card}>
              <p>{result.labels.days}</p>
              <h2>{result.total_hazard_days}</h2>
            </article>

            <article style={styles.card}>
              <p>{result.labels.threshold}</p>
              <h2>
                {result.threshold_value} {result.threshold_unit}
              </h2>
            </article>
          </section>

          <section style={styles.panel}>
            <h2>Trend insight</h2>
            <p>{result.insight}</p>
          </section>

          <section style={styles.panel}>
            <h2>Yearly {result.labels.hazard} Frequency</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={result.yearly_data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="event_count"
                  name={`${result.labels.hazard} events`}
                  stroke="#2563eb"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section style={styles.panel}>
            <h2>Average Event Duration by Year</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={result.yearly_data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="average_duration_days"
                  name="Average duration (days)"
                  stroke="#7c3aed"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section style={styles.panel}>
            <h2>{result.labels.days} by Year</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={result.yearly_data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar
                  dataKey="hazard_days"
                  name={result.labels.days}
                  fill="#ea580c"
                />
              </BarChart>
            </ResponsiveContainer>
          </section>

          <section className="events-panel" style={styles.panel}>
            <div className="events-heading">
              <div>
                <span className="events-eyebrow">Event report</span>
                <h2>Detected {result.labels.hazard} Events</h2>
              </div>
              <span className="events-count">
                {result.events.length} {result.events.length === 1 ? "event" : "events"}
              </span>
            </div>

            {result.events.length === 0 ? (
              <p className="events-empty">
                No qualifying {result.labels.hazard.toLowerCase()} events found.
              </p>
            ) : (
              <div className="events-table-wrap">
                <table className="events-table" style={styles.table}>
                  <thead>
                    <tr>
                      <th>Start date</th>
                      <th>End date</th>
                      <th>Duration</th>
                      <th>Average value</th>
                      <th>{result.labels.extreme}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.events.map((event) => (
                      <tr key={event.start_date}>
                        <td>{event.start_date}</td>
                        <td>{event.end_date}</td>
                        <td>{event.duration_days} days</td>
                        <td>{event.average_value} {event.value_unit}</td>
                        <td>{event.extreme_value} {event.value_unit}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <p style={styles.note}>
            {result.methodology_note}
          </p>
        </>
      )}
    </main>
  );
}

const styles = {
  filters: {
    display: "flex",
    flexWrap: "wrap",
    gap: "16px",
    alignItems: "end",
    padding: "20px",
    background: "#f3f4f6",
    borderRadius: "12px",
  },
  cards: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap: "16px",
    margin: "24px 0",
  },
  card: {
    padding: "20px",
    background: "#eff6ff",
    borderRadius: "12px",
  },
  panel: {
    padding: "20px",
    marginTop: "20px",
    border: "1px solid #e5e7eb",
    borderRadius: "12px",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    textAlign: "left",
  },
  error: {
    color: "#b91c1c",
    marginTop: "16px",
  },
  note: {
    color: "#6b7280",
    fontSize: "13px",
    marginTop: "24px",
  },
};
