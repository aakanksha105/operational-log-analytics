# Operational Log Analytics | Python · SQL · PostgreSQL · Tableau

**A historical log analytics and anomaly-screening project that transforms raw Apache and HDFS system logs into actionable operational metrics, time-series trends, and recurring-issue investigations.**

Built with **Python, Flask, PostgreSQL, Pandas, SQL, REST APIs, and Chart.js**; the exported dataset can also be explored in **Tableau**.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/) ![Flask](https://img.shields.io/badge/Flask-REST%20API-555555) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-SQL-336791?logo=postgresql&logoColor=white) ![Pandas](https://img.shields.io/badge/Pandas-Analytics-150458?logo=pandas&logoColor=white) ![Tableau](https://img.shields.io/badge/Tableau-Visualization-E97627)

**[View Tableau dashboard](https://public.tableau.com/views/Operational_Log_Analytics/ExecutiveOverview?:showVizHome=no)** · **[Explore source data](logs_export.csv)** · **[API reference](docs/API.md)**

> **Portfolio note:** The Tableau Public visualization is a separate visualization of the exported data; the repository's screenshot gallery documents the original Flask/Chart.js application. These logs are **historical**, not live telemetry.

## Project highlights

| Metric | Value | Definition |
| --- | ---: | --- |
| Log records analyzed | **10,000** | Rows in the included CSV export |
| Apache records | **6,000** | `dataset = Loghub-Apache` |
| HDFS records | **4,000** | `dataset = Loghub-HDFS` |
| Error events | **1,785** | `severity = ERROR` |
| Warning events | **160** | `severity = WARNING` |
| Components / services | **4 HDFS + 1 Apache** | Distinct `service` values in this export |

The sample contains event timestamps from **2005–2008**. Counts above describe the included export—not ongoing production traffic.

## The problem

Unstructured system logs are difficult to compare across services and time periods. Operators need answers to practical questions:

- Where are error events concentrated?
- How does log activity change over time?
- Which services and message patterns warrant investigation?
- When does an unusual spike deserve a closer look?

This project creates a repeatable workflow from **raw logs → structured records → SQL/Pandas analysis → dashboard and reporting**.

## Dashboard and analysis

### 1. Executive overview

KPI summaries, log volumes, severity distribution, and comparisons across Apache/HDFS services.

![Original Flask operations dashboard](docs/images/Figure_1_Overall_Dashboard.png)

### 2. Trends and anomaly screening

Hourly, daily, and weekly event trends; rolling severe-event averages; changes in error volume; and statistical/threshold-based anomaly candidates.

![Time-series analytics](docs/images/Figure_3_Apache_TimeSeries_Analysis.png)

![Statistical anomaly detection](docs/images/Figure_6_Statistical_Anomaly_Detection.png)

### 3. Service performance and recurring issues

Compare log volumes and severe-event rates by service. Group frequently recurring severe messages to prioritize investigation; these patterns are **not confirmed root causes**.

![Service comparison](docs/images/Figure_4_Apache_Service_Comparison.png)

![Recurring severe-event analysis](docs/images/Figure_5_Root_Cause_Analysis.png)

Additional [dashboard, HDFS, report, and API screenshots](docs/images/) are available in the repository.

## Technical approach

1. **Ingest:** Upload Apache, HDFS, or generic logs with a Flask REST endpoint.
2. **Parse:** Normalize timestamps, severity, service, component, event type, and message text.
3. **Store:** Persist structured events with SQLAlchemy; PostgreSQL is supported, and SQLite is the default local fallback.
4. **Analyze:** Use SQL filtering and Pandas aggregations to calculate KPIs, severity breakdowns, time-series trends, rolling averages, and service comparisons.
5. **Screen anomalies:** Flag unusual activity through statistical and threshold-based methods; provide explanatory summaries for investigation.
6. **Present and export:** Explore the Flask/Chart.js dashboard, query the API, generate reports, or export results to CSV for BI tools.

![Project architecture](docs/images/Figure_10_Project_Architecture.png)

| Layer | Technologies |
| --- | --- |
| Backend and ingestion | Python, Flask, Flask-SQLAlchemy, REST |
| Storage and querying | PostgreSQL, SQLite (local fallback), SQL |
| Data analytics | Pandas, grouped KPIs, time-series aggregation, statistical screening |
| Application dashboard | Chart.js, JavaScript, HTML/CSS |
| External BI visualization | Tableau Public, using the exported CSV |
| Testing and deployment | pytest, Docker, Docker Compose |

## Data and measurement notes

The source samples are from [Loghub](https://github.com/logpai/loghub). The included [`logs_export.csv`](logs_export.csv) has **10,000 rows and 11 columns**: `id`, `batch_id`, `dataset`, `timestamp`, `severity`, `service`, `component`, `event_type`, `message`, `raw_log`, and `created_at`.

**Event time vs. ingestion time:** Use `timestamp` for historical event trends; `created_at` reflects the ingestion/export workflow and should not be treated as the original event time.

**Severity definitions:** In the code, a *severe event* means `ERROR` or `CRITICAL`. The API's `error_rate_pct` KPI uses this combined severe-event definition, whereas `error_count` counts strictly `ERROR`. For the included CSV, there are 1,785 errors and no `CRITICAL` records.

**Anomaly limitations:** A spike or threshold breach is a candidate for investigation, not a ground-truth incident label. Similarly, grouped recurring messages indicate patterns rather than verified causality. “AI-style explanations” refer to programmatic human-readable summaries; this README does not claim a deployed generative-AI model.

**Performance note:** Research work on the SQL/log-analytics implementation reported approximately **29.75% faster database queries** under a project benchmarking workload. This is a project-specific reported result, **not** a reproducible performance guarantee from the CSV alone; benchmark code, environment, and before/after measurements would be needed to validate it independently.

## Run locally

**Requirements:** Python 3.11+, pip; optional PostgreSQL.

```bash
git clone https://github.com/aakanksha105/operational-log-analytics.git
cd operational-log-analytics
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open **http://127.0.0.1:5000/dashboard**.

To run with PostgreSQL, create a database and set an environment variable before starting:

```bash
export DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/log_anomaly_loghub"
export SECRET_KEY="replace-with-a-generated-secret"
python run.py
```

The Flask app creates tables when initialized. The provided CSV is an **export**, not an automatic seed: a new database starts without those 10,000 rows until logs are imported.

### Upload a sample and use the API

```bash
curl -X POST \
  -F "file=@data/loghub/Apache_2k.log" \
  -F "dataset=Loghub-Apache" \
  http://127.0.0.1:5000/api/logs/upload

curl http://127.0.0.1:5000/api/analytics/kpis
curl http://127.0.0.1:5000/api/analytics/severity
curl "http://127.0.0.1:5000/api/analytics/error-trend?freq=1H"

curl -X POST http://127.0.0.1:5000/api/anomalies/run
curl http://127.0.0.1:5000/api/anomalies

curl http://127.0.0.1:5000/api/export/logs.csv -o local_logs_export.csv
```

See [docs/API.md](docs/API.md) for additional endpoints. Run available tests with `pytest`.

## Repository structure

```text
app/                   Flask routes, models, analytics, parsing, reporting
  templates/           Dashboard HTML
  static/              Chart.js integration, scripts, styling
data/loghub/            Apache/HDFS sample logs
docs/                   API reference and research scope
  images/              Dashboard, API, and architecture screenshots
scripts/                Dataset utilities
tests/                  Parser and analytics tests
logs_export.csv         Exported analytical dataset
run.py                  Flask entry point
requirements.txt        Python dependencies
```

## Skills demonstrated

**SQL and data modeling · ETL/log parsing · Python/Pandas analysis · KPI definition · time-series analytics · anomaly screening · REST API development · operational reporting · Tableau visualization**

---

**Author:** [Aakanksha Bhondve](https://github.com/aakanksha105)
# Operational Log Analytics | Python · SQL · PostgreSQL · Tableau

**A historical log analytics and anomaly-screening project that transforms raw Apache and HDFS system logs into actionable operational metrics, time-series trends, and recurring-issue investigations.**

Built with **Python, Flask, PostgreSQL, Pandas, SQL, REST APIs, and Chart.js**; the exported dataset can also be explored in **Tableau**.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/) ![Flask](https://img.shields.io/badge/Flask-REST%20API-555555) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-SQL-336791?logo=postgresql&logoColor=white) ![Pandas](https://img.shields.io/badge/Pandas-Analytics-150458?logo=pandas&logoColor=white) ![Tableau](https://img.shields.io/badge/Tableau-Visualization-E97627)

**[View Tableau dashboard](https://public.tableau.com/views/Operational_Log_Analytics/ExecutiveOverview?:showVizHome=no)** · **[Explore source data](logs_export.csv)** · **[API reference](docs/API.md)**

> **Portfolio note:** The Tableau Public visualization is a separate visualization of the exported data; the repository's screenshot gallery documents the original Flask/Chart.js application. These logs are **historical**, not live telemetry.

## Project highlights

| Metric | Value | Definition |
| --- | ---: | --- |
| Log records analyzed | **10,000** | Rows in the included CSV export |
| Apache records | **6,000** | `dataset = Loghub-Apache` |
| HDFS records | **4,000** | `dataset = Loghub-HDFS` |
| Error events | **1,785** | `severity = ERROR` |
| Warning events | **160** | `severity = WARNING` |
| Components / services | **4 HDFS + 1 Apache** | Distinct `service` values in this export |

The sample contains event timestamps from **2005–2008**. Counts above describe the included export—not ongoing production traffic.

## The problem

Unstructured system logs are difficult to compare across services and time periods. Operators need answers to practical questions:

- Where are error events concentrated?
- How does log activity change over time?
- Which services and message patterns warrant investigation?
- When does an unusual spike deserve a closer look?

This project creates a repeatable workflow from **raw logs → structured records → SQL/Pandas analysis → dashboard and reporting**.

## Dashboard and analysis

### 1. Executive overview

KPI summaries, log volumes, severity distribution, and comparisons across Apache/HDFS services.

![Original Flask operations dashboard](docs/images/Figure_1_Overall_Dashboard.png)

### 2. Trends and anomaly screening

Hourly, daily, and weekly event trends; rolling severe-event averages; changes in error volume; and statistical/threshold-based anomaly candidates.

![Time-series analytics](docs/images/Figure_3_Apache_TimeSeries_Analysis.png)

![Statistical anomaly detection](docs/images/Figure_6_Statistical_Anomaly_Detection.png)

### 3. Service performance and recurring issues

Compare log volumes and severe-event rates by service. Group frequently recurring severe messages to prioritize investigation; these patterns are **not confirmed root causes**.

![Service comparison](docs/images/Figure_4_Apache_Service_Comparison.png)

![Recurring severe-event analysis](docs/images/Figure_5_Root_Cause_Analysis.png)

Additional [dashboard, HDFS, report, and API screenshots](docs/images/) are available in the repository.

## Technical approach

1. **Ingest:** Upload Apache, HDFS, or generic logs with a Flask REST endpoint.
2. **Parse:** Normalize timestamps, severity, service, component, event type, and message text.
3. **Store:** Persist structured events with SQLAlchemy; PostgreSQL is supported, and SQLite is the default local fallback.
4. **Analyze:** Use SQL filtering and Pandas aggregations to calculate KPIs, severity breakdowns, time-series trends, rolling averages, and service comparisons.
5. **Screen anomalies:** Flag unusual activity through statistical and threshold-based methods; provide explanatory summaries for investigation.
6. **Present and export:** Explore the Flask/Chart.js dashboard, query the API, generate reports, or export results to CSV for BI tools.

![Project architecture](docs/images/Figure_10_Project_Architecture.png)

| Layer | Technologies |
| --- | --- |
| Backend and ingestion | Python, Flask, Flask-SQLAlchemy, REST |
| Storage and querying | PostgreSQL, SQLite (local fallback), SQL |
| Data analytics | Pandas, grouped KPIs, time-series aggregation, statistical screening |
| Application dashboard | Chart.js, JavaScript, HTML/CSS |
| External BI visualization | Tableau Public, using the exported CSV |
| Testing and deployment | pytest, Docker, Docker Compose |

## Data and measurement notes

The source samples are from [Loghub](https://github.com/logpai/loghub). The included [`logs_export.csv`](logs_export.csv) has **10,000 rows and 11 columns**: `id`, `batch_id`, `dataset`, `timestamp`, `severity`, `service`, `component`, `event_type`, `message`, `raw_log`, and `created_at`.

**Event time vs. ingestion time:** Use `timestamp` for historical event trends; `created_at` reflects the ingestion/export workflow and should not be treated as the original event time.

**Severity definitions:** In the code, a *severe event* means `ERROR` or `CRITICAL`. The API's `error_rate_pct` KPI uses this combined severe-event definition, whereas `error_count` counts strictly `ERROR`. For the included CSV, there are 1,785 errors and no `CRITICAL` records.

**Anomaly limitations:** A spike or threshold breach is a candidate for investigation, not a ground-truth incident label. Similarly, grouped recurring messages indicate patterns rather than verified causality. “AI-style explanations” refer to programmatic human-readable summaries; this README does not claim a deployed generative-AI model.

**Performance note:** Research work on the SQL/log-analytics implementation reported approximately **29.75% faster database queries** under a project benchmarking workload. This is a project-specific reported result, **not** a reproducible performance guarantee from the CSV alone; benchmark code, environment, and before/after measurements would be needed to validate it independently.

## Run locally

**Requirements:** Python 3.11+, pip; optional PostgreSQL.

```bash
git clone https://github.com/aakanksha105/operational-log-analytics.git
cd operational-log-analytics
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

Open **http://127.0.0.1:5000/dashboard**.

To run with PostgreSQL, create a database and set an environment variable before starting:

```bash
export DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/log_anomaly_loghub"
export SECRET_KEY="replace-with-a-generated-secret"
python run.py
```

The Flask app creates tables when initialized. The provided CSV is an **export**, not an automatic seed: a new database starts without those 10,000 rows until logs are imported.

### Upload a sample and use the API

```bash
curl -X POST \
  -F "file=@data/loghub/Apache_2k.log" \
  -F "dataset=Loghub-Apache" \
  http://127.0.0.1:5000/api/logs/upload

curl http://127.0.0.1:5000/api/analytics/kpis
curl http://127.0.0.1:5000/api/analytics/severity
curl "http://127.0.0.1:5000/api/analytics/error-trend?freq=1H"

curl -X POST http://127.0.0.1:5000/api/anomalies/run
curl http://127.0.0.1:5000/api/anomalies

curl http://127.0.0.1:5000/api/export/logs.csv -o local_logs_export.csv
```

See [docs/API.md](docs/API.md) for additional endpoints. Run available tests with `pytest`.

## Repository structure

```text
app/                   Flask routes, models, analytics, parsing, reporting
  templates/           Dashboard HTML
  static/              Chart.js integration, scripts, styling
data/loghub/            Apache/HDFS sample logs
docs/                   API reference and research scope
  images/              Dashboard, API, and architecture screenshots
scripts/                Dataset utilities
tests/                  Parser and analytics tests
logs_export.csv         Exported analytical dataset
run.py                  Flask entry point
requirements.txt        Python dependencies
```

## Skills demonstrated

**SQL and data modeling · ETL/log parsing · Python/Pandas analysis · KPI definition · time-series analytics · anomaly screening · REST API development · operational reporting · Tableau visualization**

---

**Author:** [Aakanksha Bhondve](https://github.com/aakanksha105)
