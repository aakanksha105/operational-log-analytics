"use strict";

const charts = {};

document.addEventListener("DOMContentLoaded", async () => {
    bindEventListeners();

    try {
        await loadFilterOptions();
        await refreshDashboard();
    } catch (error) {
        showError(error.message);
    }
});


function bindEventListeners() {
    document
        .getElementById("applyFiltersButton")
        .addEventListener("click", refreshDashboard);

    document
        .getElementById("clearFiltersButton")
        .addEventListener("click", async () => {
            clearFilters();
            await refreshDashboard();
        });

    document
        .getElementById("trendFrequency")
        .addEventListener("change", loadErrorTrend);

    document
        .getElementById("runAnomalyButton")
        .addEventListener("click", runAnomalyDetection);

    document
        .getElementById("loadDailyReportButton")
        .addEventListener("click", () => previewReport("daily"));

    document
        .getElementById("loadWeeklyReportButton")
        .addEventListener("click", () => previewReport("weekly"));
}


async function refreshDashboard() {
    hideError();
    updateFilterStatus();
    updateExportLinks();

    try {
        await Promise.all([
            loadKPIs(),
            loadSeverityChart(),
            loadServiceChart(),
            loadErrorTrend(),
            loadHourlyChart(),
            loadDailyChart(),
            loadServiceComparisonChart(),
            loadRootCausePatterns(),
            loadTopMessages(),
            loadAnomalies(),
        ]);
    } catch (error) {
        showError(error.message);
    }
}


async function getJSON(url, options = {}) {
    const response = await fetch(url, options);

    let payload;

    try {
        payload = await response.json();
    } catch {
        payload = null;
    }

    if (!response.ok) {
        const message =
            payload?.error ||
            payload?.message ||
            `Request failed with status ${response.status}`;

        throw new Error(message);
    }

    return payload;
}


function buildQuery(extraParameters = {}) {
    const params = new URLSearchParams();

    const dataset = document.getElementById("datasetFilter").value;
    const service = document.getElementById("serviceFilter").value;
    const severity = document.getElementById("severityFilter").value;
    const start = document.getElementById("startDate").value;
    const end = document.getElementById("endDate").value;

    if (dataset) {
        params.set("dataset", dataset);
    }

    if (service) {
        params.set("service", service);
    }

    if (severity) {
        params.set("severity", severity);
    }

    if (start) {
        params.set("start", start);
    }

    if (end) {
        params.set("end", end);
    }

    Object.entries(extraParameters).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
            params.set(key, value);
        }
    });

    return params.toString();
}


function withQuery(path, extraParameters = {}) {
    const query = buildQuery(extraParameters);

    return query ? `${path}?${query}` : path;
}


async function loadFilterOptions() {
    const options = await getJSON("/api/analytics/filter-options");

    populateSelect(
        "datasetFilter",
        options.datasets || [],
        "All datasets"
    );

    populateSelect(
        "serviceFilter",
        options.services || [],
        "All services"
    );

    populateSelect(
        "severityFilter",
        options.severities || [],
        "All severities"
    );
}


function populateSelect(elementId, values, defaultLabel) {
    const select = document.getElementById(elementId);
    const previousValue = select.value;

    select.innerHTML = "";

    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = defaultLabel;
    select.appendChild(defaultOption);

    values.forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        select.appendChild(option);
    });

    if (values.includes(previousValue)) {
        select.value = previousValue;
    }
}


function clearFilters() {
    document.getElementById("datasetFilter").value = "";
    document.getElementById("serviceFilter").value = "";
    document.getElementById("severityFilter").value = "";
    document.getElementById("startDate").value = "";
    document.getElementById("endDate").value = "";
}


function updateFilterStatus() {
    const labels = [];

    const dataset = document.getElementById("datasetFilter").value;
    const service = document.getElementById("serviceFilter").value;
    const severity = document.getElementById("severityFilter").value;
    const start = document.getElementById("startDate").value;
    const end = document.getElementById("endDate").value;

    if (dataset) {
        labels.push(`Dataset: ${dataset}`);
    }

    if (service) {
        labels.push(`Service: ${service}`);
    }

    if (severity) {
        labels.push(`Severity: ${severity}`);
    }

    if (start) {
        labels.push(`From: ${start}`);
    }

    if (end) {
        labels.push(`To: ${end}`);
    }

    document.getElementById("filterStatus").textContent =
        labels.length > 0
            ? labels.join(" • ")
            : "Showing all available records.";
}


function updateExportLinks() {
    document.getElementById("csvExportLink").href =
        withQuery("/api/export/logs.csv");

    document.getElementById("jsonExportLink").href =
        withQuery("/api/export/report.json");
}


async function loadKPIs() {
    const data = await getJSON(
        withQuery("/api/analytics/kpis")
    );

    setText("totalLogs", formatNumber(data.total_logs));
    setText("errorRate", `${formatDecimal(data.error_rate_pct)}%`);
    setText(
        "warningRate",
        `${formatDecimal(data.warning_rate_pct)}%`
    );
    setText(
        "criticalEvents",
        formatNumber(data.critical_events)
    );
    setText(
        "anomaliesDetected",
        formatNumber(data.anomalies_detected)
    );
    setText(
        "totalServices",
        formatNumber(data.total_services)
    );
    setText(
        "averageErrorsPerHour",
        formatDecimal(data.average_errors_per_hour)
    );

    setText(
        "mostActiveService",
        data.most_active_service || "—"
    );

    setText(
        "mostActiveServiceCount",
        `${formatNumber(
            data.most_active_service_count
        )} records`
    );
}


async function loadSeverityChart() {
    const data = await getJSON(
        withQuery("/api/analytics/severity")
    );

    replaceChart(
        "severityChart",
        {
            type: "doughnut",
            data: {
                labels: data.map((item) => item.severity),
                datasets: [
                    {
                        label: "Logs",
                        data: data.map((item) => item.count),
                        borderWidth: 1,
                    },
                ],
            },
            options: baseChartOptions({
                plugins: {
                    legend: {
                        position: "bottom",
                    },
                },
            }),
        }
    );
}


async function loadServiceChart() {
    const data = await getJSON(
        withQuery("/api/analytics/services", {
            limit: 10,
        })
    );

    replaceChart(
        "serviceChart",
        {
            type: "bar",
            data: {
                labels: data.map((item) => item.service),
                datasets: [
                    {
                        label: "Log Count",
                        data: data.map((item) => item.count),
                        borderWidth: 1,
                    },
                ],
            },
            options: baseChartOptions({
                indexAxis: "y",
                scales: {
                    x: {
                        beginAtZero: true,
                    },
                },
            }),
        }
    );
}


async function loadErrorTrend() {
    const frequency =
        document.getElementById("trendFrequency").value;

    const data = await getJSON(
        withQuery("/api/analytics/error-trend", {
            freq: frequency,
        })
    );

    replaceChart(
        "errorTrendChart",
        {
            type: "line",
            data: {
                labels: data.map((item) =>
                    formatDateTime(item.time_bucket)
                ),
                datasets: [
                    {
                        label: "Severe Events",
                        data: data.map(
                            (item) => item.severe_count
                        ),
                        tension: 0.25,
                        fill: false,
                    },
                    {
                        label: "Warnings",
                        data: data.map(
                            (item) => item.warning_count
                        ),
                        tension: 0.25,
                        fill: false,
                    },
                ],
            },
            options: timeSeriesChartOptions(),
        }
    );
}


async function loadHourlyChart() {
    const data = await getJSON(
        withQuery("/api/analytics/hourly")
    );

    replaceChart(
        "hourlyChart",
        {
            type: "line",
            data: {
                labels: data.map((item) =>
                    formatDateTime(item.time_bucket)
                ),
                datasets: [
                    {
                        label: "Severe Events",
                        data: data.map(
                            (item) => item.severe_count
                        ),
                        tension: 0.25,
                    },
                    {
                        label: "Rolling Average",
                        data: data.map(
                            (item) =>
                                item.rolling_severe_average
                        ),
                        tension: 0.25,
                        borderDash: [6, 4],
                    },
                ],
            },
            options: timeSeriesChartOptions(),
        }
    );
}


async function loadDailyChart() {
    const data = await getJSON(
        withQuery("/api/analytics/daily")
    );

    replaceChart(
        "dailyChart",
        {
            type: "bar",
            data: {
                labels: data.map((item) =>
                    formatDate(item.time_bucket)
                ),
                datasets: [
                    {
                        label: "Severe Events",
                        data: data.map(
                            (item) => item.severe_count
                        ),
                    },
                    {
                        label: "Rolling Average",
                        data: data.map(
                            (item) =>
                                item.rolling_severe_average
                        ),
                        type: "line",
                        tension: 0.25,
                    },
                ],
            },
            options: timeSeriesChartOptions(),
        }
    );
}


async function loadServiceComparisonChart() {
    const data = await getJSON(
        withQuery(
            "/api/analytics/service-comparison"
        )
    );

    const limitedData = data.slice(0, 12);

    replaceChart(
        "serviceComparisonChart",
        {
            type: "bar",
            data: {
                labels: limitedData.map(
                    (item) => item.service
                ),
                datasets: [
                    {
                        label: "Severe Event Rate %",
                        data: limitedData.map(
                            (item) => item.error_rate_pct
                        ),
                    },
                    {
                        label: "Warning Rate %",
                        data: limitedData.map(
                            (item) => item.warning_rate_pct
                        ),
                    },
                ],
            },
            options: baseChartOptions({
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "Percentage",
                        },
                    },
                },
            }),
        }
    );
}


async function loadRootCausePatterns() {
    const data = await getJSON(
        withQuery("/api/analytics/root-causes", {
            limit: 15,
        })
    );

    const tbody = document.getElementById(
        "rootCauseTableBody"
    );

    if (!data.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    No recurring severe-event patterns found.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = data
        .map(
            (item) => `
                <tr>
                    <td>${escapeHTML(item.service)}</td>
                    <td>
                        <span class="severity-badge severity-${severityClass(
                            item.severity
                        )}">
                            ${escapeHTML(item.severity)}
                        </span>
                    </td>
                    <td>
                        <strong>
                            ${escapeHTML(item.pattern_category)}
                        </strong>
                        <div class="secondary-text">
                            ${escapeHTML(item.message)}
                        </div>
                    </td>
                    <td>${formatNumber(item.count)}</td>
                    <td>
                        ${formatDecimal(
                            item.share_of_severe_events_pct
                        )}%
                    </td>
                    <td>
                        ${escapeHTML(
                            item.recommended_investigation
                        )}
                    </td>
                </tr>
            `
        )
        .join("");
}


async function loadTopMessages() {
    const data = await getJSON(
        withQuery("/api/analytics/top-messages", {
            limit: 10,
        })
    );

    const tbody = document.getElementById(
        "topMessagesTableBody"
    );

    if (!data.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="3" class="empty-state">
                    No recurring messages found.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = data
        .map(
            (item) => `
                <tr>
                    <td>
                        <span class="severity-badge severity-${severityClass(
                            item.severity
                        )}">
                            ${escapeHTML(item.severity)}
                        </span>
                    </td>
                    <td>${escapeHTML(item.message)}</td>
                    <td>${formatNumber(item.count)}</td>
                </tr>
            `
        )
        .join("");
}


async function loadAnomalies() {
    const payload = await getJSON(
        withQuery("/api/anomalies", {
            limit: 100,
        })
    );

    const records = payload.records || [];
    const tbody = document.getElementById(
        "anomalyTableBody"
    );

    document.getElementById(
        "anomalyStatus"
    ).textContent = `${formatNumber(
        payload.total_matching
    )} matching anomalies`;

    if (!records.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="empty-state">
                    No anomalies match the selected filters.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = records
        .map((item) => {
            const explanation =
                item.explanation ||
                item.ai_explanation ||
                {};

            const recommendation =
                explanation.recommended_action ||
                item.recommended_action ||
                "Review related logs and compare activity with the historical baseline.";

            return `
                <tr>
                    <td>${formatDateTime(item.time_bucket)}</td>
                    <td>${escapeHTML(item.dataset || "—")}</td>
                    <td>${escapeHTML(item.service || "—")}</td>
                    <td>
                        <span class="anomaly-badge">
                            ${escapeHTML(
                                String(
                                    item.anomaly_type || "unknown"
                                ).replaceAll("_", " ")
                            )}
                        </span>
                    </td>
                    <td>${formatDecimal(item.metric_value)}</td>
                    <td>${formatDecimal(item.baseline_value)}</td>
                    <td>${formatDecimal(item.threshold_value)}</td>
                    <td>${escapeHTML(item.description || "—")}</td>
                    <td>${escapeHTML(recommendation)}</td>
                </tr>
            `;
        })
        .join("");
}


async function runAnomalyDetection() {
    const button = document.getElementById(
        "runAnomalyButton"
    );

    const originalText = button.textContent;

    button.disabled = true;
    button.textContent = "Running...";

    hideError();

    try {
        const result = await getJSON(
            "/api/anomalies/run",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    rolling_window: 3,
                    z_score_threshold: 2.0,
                }),
            }
        );

        document.getElementById(
            "anomalyStatus"
        ).textContent =
            `${formatNumber(result.created)} anomalies generated`;

        await Promise.all([
            loadKPIs(),
            loadAnomalies(),
        ]);
    } catch (error) {
        showError(error.message);
    } finally {
        button.disabled = false;
        button.textContent = originalText;
    }
}


async function previewReport(reportType) {
    const preview = document.getElementById(
        "reportPreview"
    );

    preview.textContent = "Loading report...";

    try {
        const report = await getJSON(
            withQuery(`/api/report/${reportType}`)
        );

        preview.textContent = JSON.stringify(
            report,
            null,
            2
        );
    } catch (error) {
        preview.textContent = `Unable to load report: ${error.message}`;
        showError(error.message);
    }
}


function replaceChart(canvasId, configuration) {
    if (charts[canvasId]) {
        charts[canvasId].destroy();
    }

    const canvas = document.getElementById(canvasId);

    if (!canvas) {
        return;
    }

    charts[canvasId] = new Chart(
        canvas.getContext("2d"),
        configuration
    );
}


function baseChartOptions(overrides = {}) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            mode: "index",
            intersect: false,
        },
        plugins: {
            legend: {
                position: "bottom",
            },
            tooltip: {
                enabled: true,
            },
        },
        ...overrides,
    };
}


function timeSeriesChartOptions() {
    return baseChartOptions({
        scales: {
            x: {
                ticks: {
                    maxRotation: 45,
                    minRotation: 0,
                    autoSkip: true,
                    maxTicksLimit: 12,
                },
            },
            y: {
                beginAtZero: true,
            },
        },
    });
}


function setText(elementId, value) {
    const element = document.getElementById(elementId);

    if (element) {
        element.textContent = value ?? "—";
    }
}


function formatNumber(value) {
    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "0";
    }

    return new Intl.NumberFormat("en-US").format(
        numericValue
    );
}


function formatDecimal(value) {
    const numericValue = Number(value);

    if (!Number.isFinite(numericValue)) {
        return "0.00";
    }

    return numericValue.toFixed(2);
}


function formatDateTime(value) {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleString();
}


function formatDate(value) {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return String(value);
    }

    return date.toLocaleDateString();
}


function severityClass(severity) {
    return String(severity || "unknown")
        .toLowerCase()
        .replaceAll("/", "-")
        .replaceAll(" ", "-");
}


function escapeHTML(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}


function showError(message) {
    const banner = document.getElementById("errorBanner");

    banner.textContent = message;
    banner.classList.remove("hidden");
}


function hideError() {
    const banner = document.getElementById("errorBanner");

    banner.textContent = "";
    banner.classList.add("hidden");
}