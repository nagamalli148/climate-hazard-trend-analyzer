function escapeCsvCell(value) {
  const isText = typeof value === "string";
  let text = value == null ? "" : String(value);
  if (isText && /^[=+\-@\t\r]/.test(text)) {
    text = `'${text}`;
  }

  return `"${text.replaceAll('"', '""')}"`;
}

export function buildAnalysisCsv(result) {
  const rows = [
    ["Climate Hazard Trend Analyzer"],
    ["Hazard", result.labels.hazard],
    [
      "Coordinates",
      `${result.location.latitude}, ${result.location.longitude}`,
    ],
    [
      "Analysis period",
      `${result.analysis_period.start_year} to ${result.analysis_period.end_year}`,
    ],
    ["Baseline period", result.baseline_period],
    [
      "Threshold",
      `${result.threshold_value} ${result.threshold_unit}`,
    ],
    ["Threshold percentile", result.threshold_percentile],
    ["Total events", result.total_events],
    ["Total hazard days", result.total_hazard_days],
    ["Frequency trend", result.trend.frequency_direction],
    ["Events per decade", result.trend.events_per_decade],
    ["Duration trend", result.trend.duration_direction],
    [
      "Average duration days per decade",
      result.trend.average_duration_days_per_decade,
    ],
    ["Insight", result.insight],
    ["Methodology", result.methodology_note],
    [],
    ["Yearly summary"],
    [
      "Year",
      "Event count",
      result.labels.days,
      "Average event duration (days)",
    ],
    ...result.yearly_data.map((year) => [
      year.year,
      year.event_count,
      year.hazard_days,
      year.average_duration_days,
    ]),
    [],
    ["Detected events"],
    [
      "Start date",
      "End date",
      "Duration (days)",
      "Average value",
      result.labels.extreme,
      ...(result.hazard === "heavy_rainfall"
        ? ["Total precipitation (mm)"]
        : []),
    ],
    ...result.events.map((event) => [
      event.start_date,
      event.end_date,
      event.duration_days,
      `${event.average_value} ${event.value_unit}`,
      `${event.extreme_value} ${event.value_unit}`,
      ...(result.hazard === "heavy_rainfall"
        ? [event.total_precipitation_mm]
        : []),
    ]),
  ];

  return `\uFEFF${rows
    .map((row) => row.map(escapeCsvCell).join(","))
    .join("\r\n")}\r\n`;
}
