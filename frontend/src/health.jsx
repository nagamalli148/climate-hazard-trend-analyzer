import { useEffect, useState } from "react";

function App() {
  const [status, setStatus] = useState("Checking backend...");

  useEffect(() => {
    fetch("/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Backend request failed");
        }
        return response.json();
      })
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("Backend connection failed"));
  }, []);
  return (
    <main>
      <h1>Climate Hazard Trend Analyzer</h1>
      <p>Backend status: {status}</p>
    </main>
  );
}

export default App;