from __future__ import annotations


def test_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["status"] == "ok"


def test_filter_options(client):
    response = client.get(
        "/api/analytics/filter-options"
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert "datasets" in payload
    assert "services" in payload
    assert "severities" in payload


def test_kpis(client):
    response = client.get(
        "/api/analytics/kpis"
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert "total_logs" in payload
    assert "error_rate_pct" in payload
    assert "warning_rate_pct" in payload
    assert "total_services" in payload
    assert "average_errors_per_hour" in payload


def test_hourly_analytics(client):
    response = client.get(
        "/api/analytics/hourly"
    )

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_daily_analytics(client):
    response = client.get(
        "/api/analytics/daily"
    )

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_weekly_analytics(client):
    response = client.get(
        "/api/analytics/weekly"
    )

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_service_comparison(client):
    response = client.get(
        "/api/analytics/service-comparison"
    )

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_root_causes(client):
    response = client.get(
        "/api/analytics/root-causes"
    )

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)


def test_daily_report(client):
    response = client.get(
        "/api/report/daily"
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["report_type"] == "daily"
    assert "kpis" in payload
    assert "daily_trend" in payload


def test_weekly_report(client):
    response = client.get(
        "/api/report/weekly"
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert payload["report_type"] == "weekly"
    assert "kpis" in payload
    assert "weekly_trend" in payload


def test_json_export(client):
    response = client.get(
        "/api/export/report.json"
    )

    assert response.status_code == 200
    assert response.mimetype == "application/json"

    content_disposition = response.headers.get(
        "Content-Disposition",
        "",
    )

    assert "operational_summary_report.json" in content_disposition


def test_filtered_kpis(client):
    response = client.get(
        "/api/analytics/kpis?severity=ERROR"
    )

    assert response.status_code == 200

    payload = response.get_json()

    assert "total_logs" in payload


def test_filtered_hourly_analytics(client):
    response = client.get(
        "/api/analytics/hourly?service=apache-server"
    )

    assert response.status_code == 200
    assert isinstance(response.get_json(), list)