
import { useState } from "react";
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

  return (
    <main style={styles.page}>
      <h1>Climate Hazard Trend Analyzer</h1>
      <p>Explore historical heatwave patterns for a region.</p>

      <section style={styles.filters}>

       <label>
  Hazard Type
  <select
    value={hazardType}
    onChange={(e) => setHazardType(e.target.value)}
  >
    <option value="heatwave">Heatwave</option>
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
          <section style={styles.cards}>
            <article style={styles.card}>
              <p>Total events</p>
              <h2>{result.total_events}</h2>
            </article>

            <article style={styles.card}>
              <p>Heatwave days</p>
              <h2>{result.total_heatwave_days}</h2>
            </article>

            <article style={styles.card}>
              <p>95th-percentile threshold</p>
              <h2>{result.threshold_celsius}°C</h2>
            </article>
          </section>

          <section style={styles.panel}>
            <h2>Yearly Heatwave Frequency</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={result.yearly_data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="event_count"
                  name="Heatwave events"
                  stroke="#2563eb"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </section>

          <section style={styles.panel}>
            <h2>Heatwave Days by Year</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={result.yearly_data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar
                  dataKey="heatwave_days"
                  name="Heatwave days"
                  fill="#ea580c"
                />
              </BarChart>
            </ResponsiveContainer>
          </section>

          <section style={styles.panel}>
            <h2>Detected Events</h2>

            {result.events.length === 0 ? (
              <p>No qualifying heatwave events found.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th>Start date</th>
                      <th>End date</th>
                      <th>Duration</th>
                      <th>Average temperature</th>
                      <th>Maximum temperature</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.events.map((event) => (
                      <tr key={event.start_date}>
                        <td>{event.start_date}</td>
                        <td>{event.end_date}</td>
                        <td>{event.duration_days} days</td>
                        <td>{event.average_temperature}°C</td>
                        <td>{event.max_temperature}°C</td>
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
  page: {
    maxWidth: "1200px",
    margin: "0 auto",
    padding: "24px",
    fontFamily: "Arial, sans-serif",
    color: "#1f2937",
  },
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
