from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Optional

from flask import Blueprint, Response, jsonify, request

from app.extensions import db
from app.models import Anomaly, LogRecord, UploadBatch
from app.services.analytics import (
    daily_analysis,
    error_trend,
    get_filter_options,
    get_kpis,
    hourly_analysis,
    logs_to_dataframe,
    parse_filters,
    root_cause_patterns,
    run_anomaly_detection,
    service_comparison,
    service_distribution,
    severity_distribution,
    top_messages,
    weekly_analysis,
)
from app.services.parser import infer_dataset_name, parse_lines
from app.services.reporting import (
    build_daily_report,
    build_summary_report,
    build_weekly_report,
)

api_bp = Blueprint("api", __name__)


# ---------------------------------------------------------------------------
# General helpers
# ---------------------------------------------------------------------------

def _parse_positive_int(
    value: Optional[str],
    default: int,
    maximum: int,
) -> int:
    try:
        parsed = int(value or default)
    except (TypeError, ValueError):
        return default

    return max(0, min(parsed, maximum))


def _parse_iso_datetime(
    value: Optional[str],
    end_of_day: bool = False,
) -> Optional[datetime]:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if end_of_day and len(value) == 10:
        parsed = parsed.replace(
            hour=23,
            minute=59,
            second=59,
            microsecond=999999,
        )

    return parsed


def _apply_log_filters(query):
    severity = request.args.get("severity") or request.args.get("level")
    service = request.args.get("service")
    dataset = request.args.get("dataset")
    start = _parse_iso_datetime(request.args.get("start"))
    end = _parse_iso_datetime(
        request.args.get("end"),
        end_of_day=True,
    )

    if severity:
        query = query.filter(
            LogRecord.severity == severity.strip().upper()
        )

    if service:
        query = query.filter(
            LogRecord.service == service.strip()
        )

    if dataset:
        query = query.filter(
            LogRecord.dataset == dataset.strip()
        )

    if start:
        query = query.filter(
            LogRecord.timestamp >= start
        )

    if end:
        query = query.filter(
            LogRecord.timestamp <= end
        )

    return query


def _apply_anomaly_filters(query):
    severity = request.args.get("severity") or request.args.get("level")
    service = request.args.get("service")
    dataset = request.args.get("dataset")
    anomaly_type = request.args.get("anomaly_type")
    start = _parse_iso_datetime(request.args.get("start"))
    end = _parse_iso_datetime(
        request.args.get("end"),
        end_of_day=True,
    )

    if severity:
        query = query.filter(
            Anomaly.severity.ilike(
                f"%{severity.strip().upper()}%"
            )
        )

    if service:
        query = query.filter(
            Anomaly.service == service.strip()
        )

    if dataset:
        query = query.filter(
            Anomaly.dataset == dataset.strip()
        )

    if anomaly_type:
        query = query.filter(
            Anomaly.anomaly_type == anomaly_type.strip()
        )

    if start:
        query = query.filter(
            Anomaly.time_bucket >= start
        )

    if end:
        query = query.filter(
            Anomaly.time_bucket <= end
        )

    return query


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@api_bp.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "message": "Loghub Log Analytics API is running",
        }
    )


# ---------------------------------------------------------------------------
# Upload and log retrieval
# ---------------------------------------------------------------------------

@api_bp.post("/logs/upload")
def upload_logs():
    if "file" not in request.files:
        return (
            jsonify(
                {
                    "error": (
                        "No file uploaded. Use multipart field named 'file'."
                    )
                }
            ),
            400,
        )

    uploaded = request.files["file"]

    if not uploaded.filename:
        return jsonify({"error": "Uploaded filename is empty"}), 400

    dataset = (
        request.form.get("dataset")
        or request.form.get("dataset_type")
        or infer_dataset_name(uploaded.filename)
    )

    dataset = dataset.strip()

    try:
        content = uploaded.read().decode(
            "utf-8",
            errors="ignore",
        )
    except Exception as exc:
        return (
            jsonify(
                {
                    "error": "Unable to read uploaded file",
                    "details": str(exc),
                }
            ),
            400,
        )

    parsed_records = parse_lines(
        content.splitlines(),
        dataset=dataset,
    )

    if not parsed_records:
        return (
            jsonify(
                {
                    "error": "No valid log records could be parsed",
                    "dataset": dataset,
                    "filename": uploaded.filename,
                }
            ),
            400,
        )

    try:
        batch = UploadBatch(
            filename=uploaded.filename,
            dataset_name=dataset,
            parser_used="apache/hdfs/generic-auto",
            records_inserted=len(parsed_records),
        )

        db.session.add(batch)
        db.session.flush()

        log_records = [
            LogRecord(
                batch_id=batch.id,
                **record,
            )
            for record in parsed_records
        ]

        db.session.bulk_save_objects(log_records)
        db.session.commit()

    except Exception as exc:
        db.session.rollback()

        return (
            jsonify(
                {
                    "error": "Database insertion failed",
                    "details": str(exc),
                }
            ),
            500,
        )

    return (
        jsonify(
            {
                "message": "Logs uploaded and processed successfully",
                "dataset": dataset,
                "filename": uploaded.filename,
                "records_inserted": len(parsed_records),
                "batch_id": batch.id,
            }
        ),
        201,
    )


@api_bp.get("/logs")
def list_logs():
    query = _apply_log_filters(LogRecord.query)

    limit = _parse_positive_int(
        request.args.get("limit"),
        default=100,
        maximum=1000,
    )

    offset = _parse_positive_int(
        request.args.get("offset"),
        default=0,
        maximum=1_000_000,
    )

    total_matching = query.count()

    records = (
        query.order_by(
            LogRecord.timestamp.desc().nullslast(),
            LogRecord.id.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "total_matching": total_matching,
            "limit": limit,
            "offset": offset,
            "records": [
                record.to_dict()
                for record in records
            ],
        }
    )


@api_bp.get("/logs/summary")
def log_summary():
    filters = parse_filters(request.args)

    return jsonify(
        {
            "filters": filters,
            "kpis": get_kpis(filters),
            "by_severity": severity_distribution(filters),
            "by_service": service_distribution(filters),
            "top_messages": top_messages(
                limit=_parse_positive_int(
                    request.args.get("limit"),
                    default=10,
                    maximum=100,
                ),
                filters=filters,
            ),
        }
    )


# ---------------------------------------------------------------------------
# Report 4 analytics routes — now with filter support
# ---------------------------------------------------------------------------

@api_bp.get("/analytics/kpis")
def kpis():
    filters = parse_filters(request.args)
    return jsonify(get_kpis(filters))


@api_bp.get("/analytics/severity")
def severity():
    filters = parse_filters(request.args)
    return jsonify(severity_distribution(filters))


@api_bp.get("/analytics/services")
def services():
    filters = parse_filters(request.args)

    limit = _parse_positive_int(
        request.args.get("limit"),
        default=10,
        maximum=100,
    )

    return jsonify(
        service_distribution(
            filters=filters,
            limit=limit,
        )
    )


@api_bp.get("/analytics/error-trend")
def trend():
    filters = parse_filters(request.args)
    frequency = request.args.get("freq", "15min")

    allowed_frequencies = {
        "5min",
        "15min",
        "30min",
        "1h",
        "6h",
        "12h",
        "1d",
        "1W",
    }

    if frequency not in allowed_frequencies:
        return (
            jsonify(
                {
                    "error": "Unsupported frequency",
                    "allowed": sorted(allowed_frequencies),
                }
            ),
            400,
        )

    return jsonify(
        error_trend(
            freq=frequency,
            filters=filters,
        )
    )


@api_bp.get("/analytics/top-messages")
def messages():
    filters = parse_filters(request.args)

    limit = _parse_positive_int(
        request.args.get("limit"),
        default=10,
        maximum=100,
    )

    return jsonify(
        top_messages(
            limit=limit,
            filters=filters,
        )
    )


# ---------------------------------------------------------------------------
# Report 5 analytics routes
# ---------------------------------------------------------------------------

@api_bp.get("/analytics/filter-options")
def filter_options():
    return jsonify(get_filter_options())


@api_bp.get("/analytics/hourly")
def hourly():
    filters = parse_filters(request.args)
    return jsonify(hourly_analysis(filters))


@api_bp.get("/analytics/daily")
def daily():
    filters = parse_filters(request.args)
    return jsonify(daily_analysis(filters))


@api_bp.get("/analytics/weekly")
def weekly():
    filters = parse_filters(request.args)
    return jsonify(weekly_analysis(filters))


@api_bp.get("/analytics/service-comparison")
def compare_services():
    filters = parse_filters(request.args)
    return jsonify(service_comparison(filters))


@api_bp.get("/analytics/root-causes")
def root_causes():
    filters = parse_filters(request.args)

    limit = _parse_positive_int(
        request.args.get("limit"),
        default=15,
        maximum=100,
    )

    return jsonify(
        root_cause_patterns(
            filters=filters,
            limit=limit,
        )
    )


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

@api_bp.post("/anomalies/run")
def run_anomalies():
    payload = request.get_json(silent=True) or {}

    try:
        rolling_window = int(
            payload.get(
                "rolling_window",
                request.args.get("rolling_window", 3),
            )
        )

        z_score_threshold = float(
            payload.get(
                "z_score_threshold",
                request.args.get("z_score_threshold", 2.0),
            )
        )

    except (TypeError, ValueError):
        return (
            jsonify(
                {
                    "error": (
                        "rolling_window must be an integer and "
                        "z_score_threshold must be numeric"
                    )
                }
            ),
            400,
        )

    if rolling_window < 2 or rolling_window > 48:
        return (
            jsonify(
                {
                    "error": (
                        "rolling_window must be between 2 and 48"
                    )
                }
            ),
            400,
        )

    if z_score_threshold <= 0 or z_score_threshold > 10:
        return (
            jsonify(
                {
                    "error": (
                        "z_score_threshold must be greater than 0 "
                        "and no more than 10"
                    )
                }
            ),
            400,
        )

    result = run_anomaly_detection(
        clear_existing=True,
        rolling_window=rolling_window,
        z_score_threshold=z_score_threshold,
    )

    return jsonify(result)


@api_bp.get("/anomalies")
def get_anomalies():
    query = _apply_anomaly_filters(Anomaly.query)

    limit = _parse_positive_int(
        request.args.get("limit"),
        default=200,
        maximum=1000,
    )

    offset = _parse_positive_int(
        request.args.get("offset"),
        default=0,
        maximum=1_000_000,
    )

    total_matching = query.count()

    records = (
        query.order_by(
            Anomaly.time_bucket.desc().nullslast(),
            Anomaly.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            "total_matching": total_matching,
            "limit": limit,
            "offset": offset,
            "records": [
                record.to_dict()
                for record in records
            ],
        }
    )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

@api_bp.get("/report/daily")
def daily_report():
    filters = parse_filters(request.args)
    return jsonify(build_daily_report(filters))


@api_bp.get("/report/weekly")
def weekly_report():
    filters = parse_filters(request.args)
    return jsonify(build_weekly_report(filters))


@api_bp.get("/export/report.json")
def export_json_report():
    filters = parse_filters(request.args)
    report = build_summary_report(filters)

    output = json.dumps(
        report,
        indent=2,
        default=str,
    )

    return Response(
        output,
        mimetype="application/json",
        headers={
            "Content-Disposition": (
                "attachment; filename=operational_summary_report.json"
            )
        },
    )


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

@api_bp.get("/export/logs.csv")
def export_logs_csv():
    query = _apply_log_filters(LogRecord.query)

    records = (
        query.order_by(
            LogRecord.timestamp.asc().nullslast(),
            LogRecord.id.asc(),
        )
        .all()
    )

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow(
        [
            "id",
            "batch_id",
            "dataset",
            "timestamp",
            "severity",
            "service",
            "component",
            "event_type",
            "message",
            "raw_log",
            "created_at",
        ]
    )

    for record in records:
        writer.writerow(
            [
                record.id,
                record.batch_id,
                record.dataset,
                (
                    record.timestamp.isoformat()
                    if record.timestamp
                    else ""
                ),
                record.severity,
                record.service,
                record.component,
                record.event_type,
                record.message,
                record.raw_log,
                (
                    record.created_at.isoformat()
                    if record.created_at
                    else ""
                ),
            ]
        )

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": (
                "attachment; filename=logs_export.csv"
            )
        },
    )