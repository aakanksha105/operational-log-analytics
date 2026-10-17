# API Reference

## Health
GET `/api/health`

## Upload logs
POST `/api/logs/upload`

Form-data:
- `file`: log file
- `dataset` optional dataset label

## Query logs
GET `/api/logs?severity=ERROR&service=apache-server&limit=100`

## Summary
GET `/api/logs/summary`

## KPI metrics
GET `/api/analytics/kpis`

## Dashboard data
GET `/api/analytics/severity`
GET `/api/analytics/services`
GET `/api/analytics/error-trend?freq=1H`
GET `/api/analytics/top-messages`

## Anomaly detection
POST `/api/anomalies/run`
GET `/api/anomalies`

## Export
GET `/api/export/logs.csv`
