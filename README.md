# Log Analysis and Anomaly Detection System with AI-based Explanation

A BI/Data-focused operational log analytics platform built with Python, Flask, PostgreSQL, Pandas, and Chart.js.

This project keeps the original OPT scope: build a system that analyzes system logs to detect anomalies such as error spikes or unusual activity using simple statistical methods, with an optional AI-style component to generate explanations for identified issues. It includes backend APIs, structured log processing, data storage, analytics, anomaly detection, and a dashboard interface.

## Recommended dataset

Use **Loghub Apache** as the primary BI/dashboard dataset because it contains real server log messages with useful severity levels such as `notice` and `error`. This makes it stronger for BI/Data Analyst storytelling: error rates, severity distribution, service monitoring, and trend analysis.

Use **Loghub HDFS** as an optional second dataset for anomaly-detection research context because HDFS is commonly used in log anomaly detection work and has labeled/preprocessed variants in the Loghub ecosystem.

Included files:
- `data/loghub/Apache_2k.log` — primary real Loghub sample for dashboard/report screenshots.
- `data/loghub/HDFS_2k.log` — optional Loghub system log sample.
- `data/demo/demo_ops_5000.log` can be generated for local stress testing only.

## Features

- Upload and parse Loghub Apache/HDFS/generic log files
- Store structured records in PostgreSQL
- Query/filter logs by severity, service, dataset, and time range
- BI metrics: total logs, error rate, critical events, most active service
- Severity and service distributions
- Error trend over time
- Top recurring messages
- Threshold-based anomaly detection
- AI-style explanations for detected anomalies
- Interactive dashboard
- CSV export
- Docker support
- Parser tests

## Setup on Mac

```bash
cd /Users/aakanksha/Downloads
unzip log-anomaly-loghub-platform-complete.zip
cd log-anomaly-loghub-platform
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create your secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Create `.env`:

```bash
cp .env.example .env
```

Update `.env`:

```env
FLASK_ENV=development
SECRET_KEY=paste_generated_key_here
DATABASE_URL=postgresql://aakanksha@localhost:5432/log_anomaly_loghub
```

Start PostgreSQL:

```bash
brew services start postgresql@14
createdb log_anomaly_loghub
```

Run the app:

```bash
python run.py
```

Open:

```text
http://127.0.0.1:5000/dashboard
```

## Load the recommended Loghub Apache dataset

In a second terminal:

```bash
cd /Users/aakanksha/Downloads/log-anomaly-loghub-platform
source venv/bin/activate
curl -X POST -F "file=@data/loghub/Apache_2k.log" -F "dataset=Loghub-Apache" http://127.0.0.1:5000/api/logs/upload
```

Run anomaly detection:

```bash
curl -X POST http://127.0.0.1:5000/api/anomalies/run
```

Check APIs:

```bash
curl http://127.0.0.1:5000/api/analytics/kpis
curl http://127.0.0.1:5000/api/analytics/severity
curl http://127.0.0.1:5000/api/analytics/error-trend?freq=1H
curl http://127.0.0.1:5000/api/anomalies
```

Export data:

```bash
curl http://127.0.0.1:5000/api/export/logs.csv -o logs_export.csv
```

## Optional: refresh Loghub samples

```bash
python scripts/download_loghub_samples.py
```

## What to screenshot for Report 4

1. Dashboard KPI cards
2. Severity distribution chart
3. Error volume over time chart
4. Top recurring messages table
5. Anomaly Explorer after running detection

## Interview explanation

I built a Flask and PostgreSQL log analytics platform that ingests real Loghub system logs, parses them into structured fields, stores them for querying, generates BI-style metrics, performs exploratory analysis with Pandas, detects error spikes and unusual activity using statistical thresholds, and presents insights through an operational monitoring dashboard.
