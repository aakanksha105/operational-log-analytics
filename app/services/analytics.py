from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import func

from app.extensions import db
from app.models import AIExplanation, Anomaly, LogRecord


SEVERE_LEVELS = {"ERROR", "CRITICAL"}
DEFAULT_ROLLING_WINDOW = 3
DEFAULT_Z_SCORE_THRESHOLD = 2.0


# ---------------------------------------------------------------------------
# Filter and dataframe helpers
# ---------------------------------------------------------------------------

def parse_filters(args: Any) -> Dict[str, Optional[str]]:
    """
    Convert Flask request arguments into a consistent filter dictionary.

    Supported filters:
    - dataset
    - service
    - severity or level
    - start
    - end
    """
    return {
        "dataset": _clean_value(args.get("dataset")),
        "service": _clean_value(args.get("service")),
        "severity": _clean_value(
            args.get("severity") or args.get("level")
        ),
        "start": _clean_value(args.get("start")),
        "end": _clean_value(args.get("end")),
    }


def logs_to_dataframe(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> pd.DataFrame:
    """
    Load log records from PostgreSQL into a Pandas DataFrame.

    Filters are applied in SQL before converting data into a DataFrame.
    """
    query = LogRecord.query
    filters = filters or {}

    dataset = filters.get("dataset")
    service = filters.get("service")
    severity = filters.get("severity")
    start = _parse_datetime(filters.get("start"))
    end = _parse_datetime(filters.get("end"), end_of_day=True)

    if dataset:
        query = query.filter(LogRecord.dataset == dataset)

    if service:
        query = query.filter(LogRecord.service == service)

    if severity:
        query = query.filter(
            LogRecord.severity == severity.upper()
        )

    if start:
        query = query.filter(LogRecord.timestamp >= start)

    if end:
        query = query.filter(LogRecord.timestamp <= end)

    records = query.all()
    rows = [record.to_dict() for record in records]

    columns = [
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

    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows)

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce",
    )

    df["created_at"] = pd.to_datetime(
        df["created_at"],
        errors="coerce",
    )

    text_columns = [
        "dataset",
        "severity",
        "service",
        "component",
        "event_type",
        "message",
    ]

    for column in text_columns:
        if column in df.columns:
            df[column] = df[column].fillna("unknown")

    df["severity"] = df["severity"].str.upper()
    df["is_severe"] = df["severity"].isin(SEVERE_LEVELS)
    df["is_error"] = df["severity"] == "ERROR"
    df["is_warning"] = df["severity"] == "WARNING"
    df["is_critical"] = df["severity"] == "CRITICAL"

    return df


def get_filter_options() -> Dict[str, List[str]]:
    """Return distinct filter values for the dashboard."""
    datasets = [
        value[0]
        for value in (
            db.session.query(LogRecord.dataset)
            .filter(LogRecord.dataset.isnot(None))
            .distinct()
            .order_by(LogRecord.dataset)
            .all()
        )
        if value[0]
    ]

    services = [
        value[0]
        for value in (
            db.session.query(LogRecord.service)
            .filter(LogRecord.service.isnot(None))
            .distinct()
            .order_by(LogRecord.service)
            .all()
        )
        if value[0]
    ]

    severities = [
        value[0]
        for value in (
            db.session.query(LogRecord.severity)
            .filter(LogRecord.severity.isnot(None))
            .distinct()
            .order_by(LogRecord.severity)
            .all()
        )
        if value[0]
    ]

    return {
        "datasets": datasets,
        "services": services,
        "severities": severities,
    }


# ---------------------------------------------------------------------------
# KPI and Report 4 analytics
# ---------------------------------------------------------------------------

def get_kpis(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> Dict[str, Any]:
    """
    Generate filtered KPI metrics used by the Report 4 and Report 5 dashboards.
    """
    df = logs_to_dataframe(filters)

    if df.empty:
        return {
            "total_logs": 0,
            "severe_events": 0,
            "error_count": 0,
            "warning_count": 0,
            "critical_events": 0,
            "error_rate_pct": 0.0,
            "warning_rate_pct": 0.0,
            "critical_rate_pct": 0.0,
            "total_services": 0,
            "most_active_service": None,
            "most_active_service_count": 0,
            "average_errors_per_hour": 0.0,
            "anomalies_detected": _filtered_anomaly_count(filters),
        }

    total_logs = len(df)
    severe_events = int(df["is_severe"].sum())
    error_count = int(df["is_error"].sum())
    warning_count = int(df["is_warning"].sum())
    critical_count = int(df["is_critical"].sum())

    service_counts = (
        df["service"]
        .replace("", "unknown")
        .value_counts()
    )

    most_active_service = (
        str(service_counts.index[0])
        if not service_counts.empty
        else None
    )

    most_active_count = (
        int(service_counts.iloc[0])
        if not service_counts.empty
        else 0
    )

    timestamped = df.dropna(subset=["timestamp"]).copy()

    if timestamped.empty:
        average_errors_per_hour = 0.0
    else:
        hourly_errors = (
            timestamped.set_index("timestamp")
            .resample("1h")["is_error"]
            .sum()
        )

        average_errors_per_hour = round(
            float(hourly_errors.mean())
            if not hourly_errors.empty
            else 0.0,
            2,
        )

    return {
        "total_logs": int(total_logs),
        "severe_events": severe_events,
        "error_count": error_count,
        "warning_count": warning_count,
        "critical_events": critical_count,
        "error_rate_pct": _percentage(
            severe_events,
            total_logs,
        ),
        "warning_rate_pct": _percentage(
            warning_count,
            total_logs,
        ),
        "critical_rate_pct": _percentage(
            critical_count,
            total_logs,
        ),
        "total_services": int(df["service"].nunique()),
        "most_active_service": most_active_service,
        "most_active_service_count": most_active_count,
        "average_errors_per_hour": average_errors_per_hour,
        "anomalies_detected": _filtered_anomaly_count(filters),
    }


def severity_distribution(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> List[Dict[str, Any]]:
    df = logs_to_dataframe(filters)

    if df.empty:
        return []

    counts = (
        df.groupby("severity", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    return [
        {
            "severity": str(row["severity"]),
            "count": int(row["count"]),
        }
        for _, row in counts.iterrows()
    ]


def service_distribution(
    filters: Optional[Dict[str, Optional[str]]] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    df = logs_to_dataframe(filters)

    if df.empty:
        return []

    counts = (
        df.groupby("service", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(limit)
    )

    return [
        {
            "service": str(row["service"]),
            "count": int(row["count"]),
        }
        for _, row in counts.iterrows()
    ]


def error_trend(
    freq: str = "15min",
    filters: Optional[Dict[str, Optional[str]]] = None,
) -> List[Dict[str, Any]]:
    df = _timestamped_dataframe(filters)

    if df.empty:
        return []

    trend = (
        df.set_index("timestamp")
        .resample(freq)
        .agg(
            total_logs=("id", "count"),
            error_count=("is_error", "sum"),
            warning_count=("is_warning", "sum"),
            critical_count=("is_critical", "sum"),
            severe_count=("is_severe", "sum"),
        )
        .reset_index()
    )

    return [
        {
            "time_bucket": row["timestamp"].isoformat(),
            "total_logs": int(row["total_logs"]),
            "error_count": int(row["error_count"]),
            "warning_count": int(row["warning_count"]),
            "critical_count": int(row["critical_count"]),
            "severe_count": int(row["severe_count"]),
        }
        for _, row in trend.iterrows()
    ]


def top_messages(
    limit: int = 10,
    filters: Optional[Dict[str, Optional[str]]] = None,
) -> List[Dict[str, Any]]:
    df = logs_to_dataframe(filters)

    if df.empty:
        return []

    grouped = (
        df.groupby(
            ["message", "severity"],
            dropna=False,
        )
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(limit)
    )

    return [
        {
            "message": str(row["message"]),
            "severity": str(row["severity"]),
            "count": int(row["count"]),
        }
        for _, row in grouped.iterrows()
    ]


# ---------------------------------------------------------------------------
# Report 5 time-series analytics
# ---------------------------------------------------------------------------

def hourly_analysis(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> List[Dict[str, Any]]:
    return _time_series_analysis(
        frequency="1h",
        filters=filters,
        rolling_window=DEFAULT_ROLLING_WINDOW,
    )


def daily_analysis(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> List[Dict[str, Any]]:
    return _time_series_analysis(
        frequency="1d",
        filters=filters,
        rolling_window=DEFAULT_ROLLING_WINDOW,
    )


def weekly_analysis(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> List[Dict[str, Any]]:
    return _time_series_analysis(
        frequency="1W",
        filters=filters,
        rolling_window=DEFAULT_ROLLING_WINDOW,
    )


def _time_series_analysis(
    frequency: str,
    filters: Optional[Dict[str, Optional[str]]] = None,
    rolling_window: int = DEFAULT_ROLLING_WINDOW,
) -> List[Dict[str, Any]]:
    df = _timestamped_dataframe(filters)

    if df.empty:
        return []

    trend = (
        df.set_index("timestamp")
        .resample(frequency)
        .agg(
            total_logs=("id", "count"),
            error_count=("is_error", "sum"),
            warning_count=("is_warning", "sum"),
            critical_count=("is_critical", "sum"),
            severe_count=("is_severe", "sum"),
        )
        .reset_index()
    )

    trend["error_rate_pct"] = (
        trend["severe_count"]
        .div(trend["total_logs"].replace(0, pd.NA))
        .mul(100)
        .fillna(0)
        .round(2)
    )

    trend["rolling_severe_average"] = (
        trend["severe_count"]
        .rolling(
            window=rolling_window,
            min_periods=1,
        )
        .mean()
        .round(2)
    )

    trend["severe_change_pct"] = (
        trend["severe_count"]
        .pct_change()
        .replace([float("inf"), float("-inf")], pd.NA)
        .fillna(0)
        .mul(100)
        .round(2)
    )

    return [
        {
            "time_bucket": row["timestamp"].isoformat(),
            "total_logs": int(row["total_logs"]),
            "error_count": int(row["error_count"]),
            "warning_count": int(row["warning_count"]),
            "critical_count": int(row["critical_count"]),
            "severe_count": int(row["severe_count"]),
            "error_rate_pct": float(row["error_rate_pct"]),
            "rolling_severe_average": float(
                row["rolling_severe_average"]
            ),
            "severe_change_pct": float(
                row["severe_change_pct"]
            ),
        }
        for _, row in trend.iterrows()
    ]


# ---------------------------------------------------------------------------
# Report 5 service and root-cause analytics
# ---------------------------------------------------------------------------

def service_comparison(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> List[Dict[str, Any]]:
    df = logs_to_dataframe(filters)

    if df.empty:
        return []

    grouped = (
        df.groupby("service", dropna=False)
        .agg(
            total_logs=("id", "count"),
            error_count=("is_error", "sum"),
            warning_count=("is_warning", "sum"),
            critical_count=("is_critical", "sum"),
            severe_count=("is_severe", "sum"),
        )
        .reset_index()
    )

    grouped["error_rate_pct"] = (
        grouped["severe_count"]
        .div(grouped["total_logs"].replace(0, pd.NA))
        .mul(100)
        .fillna(0)
        .round(2)
    )

    grouped["warning_rate_pct"] = (
        grouped["warning_count"]
        .div(grouped["total_logs"].replace(0, pd.NA))
        .mul(100)
        .fillna(0)
        .round(2)
    )

    grouped = grouped.sort_values(
        ["error_rate_pct", "severe_count", "total_logs"],
        ascending=[False, False, False],
    )

    return [
        {
            "service": str(row["service"]),
            "total_logs": int(row["total_logs"]),
            "error_count": int(row["error_count"]),
            "warning_count": int(row["warning_count"]),
            "critical_count": int(row["critical_count"]),
            "severe_count": int(row["severe_count"]),
            "error_rate_pct": float(row["error_rate_pct"]),
            "warning_rate_pct": float(
                row["warning_rate_pct"]
            ),
        }
        for _, row in grouped.iterrows()
    ]


def root_cause_patterns(
    filters: Optional[Dict[str, Optional[str]]] = None,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """
    Generate non-AI root-cause pattern summaries from recurring severe messages.

    This does not claim that a root cause is proven. It identifies recurring
    issue patterns for operational investigation.
    """
    df = logs_to_dataframe(filters)

    if df.empty:
        return []

    severe_df = df[df["is_severe"]].copy()

    if severe_df.empty:
        return []

    grouped = (
        severe_df.groupby(
            [
                "dataset",
                "service",
                "severity",
                "message",
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        .head(limit)
    )

    total_severe = len(severe_df)

    results: List[Dict[str, Any]] = []

    for _, row in grouped.iterrows():
        message = str(row["message"])
        service = str(row["service"])
        count = int(row["count"])

        results.append(
            {
                "dataset": str(row["dataset"]),
                "service": service,
                "severity": str(row["severity"]),
                "message": message,
                "count": count,
                "share_of_severe_events_pct": _percentage(
                    count,
                    total_severe,
                ),
                "pattern_category": _categorize_message(message),
                "recommended_investigation": (
                    f"Review recurring '{message[:80]}' events for "
                    f"{service}, compare timestamps with deployments, "
                    "dependencies, configuration changes, and resource usage."
                ),
            }
        )

    return results


# ---------------------------------------------------------------------------
# Report 5 anomaly detection
# ---------------------------------------------------------------------------

def run_anomaly_detection(
    clear_existing: bool = True,
    rolling_window: int = DEFAULT_ROLLING_WINDOW,
    z_score_threshold: float = DEFAULT_Z_SCORE_THRESHOLD,
) -> Dict[str, Any]:
    """
    Run enhanced statistical anomaly detection.

    Methods:
    - Rolling mean and rolling standard deviation
    - Z-score style spike detection
    - Repeated severe-message detection
    - Unusual service-volume detection
    """
    if clear_existing:
        AIExplanation.query.delete()
        Anomaly.query.delete()
        db.session.commit()

    df = _timestamped_dataframe()

    if df.empty:
        return {
            "created": 0,
            "rolling_spikes": 0,
            "repeated_failures": 0,
            "service_activity_anomalies": 0,
            "message": "No timestamped logs found",
        }

    rolling_spikes = _detect_rolling_severe_spikes(
        df,
        rolling_window=rolling_window,
        z_score_threshold=z_score_threshold,
    )

    repeated_failures = _detect_repeated_failures(df)

    service_activity_anomalies = (
        _detect_unusual_service_activity(
            df,
            rolling_window=rolling_window,
            z_score_threshold=z_score_threshold,
        )
    )

    db.session.commit()

    total_created = (
        rolling_spikes
        + repeated_failures
        + service_activity_anomalies
    )

    return {
        "created": total_created,
        "rolling_spikes": rolling_spikes,
        "repeated_failures": repeated_failures,
        "service_activity_anomalies": service_activity_anomalies,
        "rolling_window": rolling_window,
        "z_score_threshold": z_score_threshold,
        "message": "Enhanced anomaly detection completed",
    }


def _detect_rolling_severe_spikes(
    df: pd.DataFrame,
    rolling_window: int,
    z_score_threshold: float,
) -> int:
    severe_df = df[df["is_severe"]].copy()

    if severe_df.empty:
        return 0

    hourly = (
        severe_df.set_index("timestamp")
        .groupby(["dataset", "service"])
        .resample("1h")
        .size()
        .reset_index(name="count")
    )

    if hourly.empty:
        return 0

    created = 0

    for (dataset, service), group in hourly.groupby(
        ["dataset", "service"]
    ):
        group = group.sort_values("timestamp").copy()

        group["rolling_mean"] = (
            group["count"]
            .shift(1)
            .rolling(
                window=rolling_window,
                min_periods=1,
            )
            .mean()
        )

        group["rolling_std"] = (
            group["count"]
            .shift(1)
            .rolling(
                window=rolling_window,
                min_periods=2,
            )
            .std()
            .fillna(0)
        )

        group["threshold"] = (
            group["rolling_mean"]
            + z_score_threshold * group["rolling_std"]
        )

        for _, row in group.iterrows():
            observed = float(row["count"])
            baseline = row["rolling_mean"]
            standard_deviation = float(row["rolling_std"])
            threshold = row["threshold"]

            if pd.isna(baseline) or pd.isna(threshold):
                continue

            baseline = float(baseline)
            threshold = max(float(threshold), baseline + 2, 3.0)

            if standard_deviation > 0:
                z_score = (
                    observed - baseline
                ) / standard_deviation
            else:
                z_score = (
                    observed - baseline
                    if observed > baseline
                    else 0.0
                )

            if observed >= threshold and observed >= 3:
                _save_anomaly(
                    {
                        "dataset": str(dataset),
                        "service": str(service),
                        "severity": "ERROR/CRITICAL",
                        "anomaly_type": "rolling_error_spike",
                        "time_bucket": row[
                            "timestamp"
                        ].to_pydatetime(),
                        "metric_name": (
                            "severe_events_per_hour"
                        ),
                        "metric_value": observed,
                        "baseline_value": round(
                            baseline,
                            2,
                        ),
                        "threshold_value": round(
                            threshold,
                            2,
                        ),
                        "description": (
                            f"{service} generated {int(observed)} severe "
                            f"events compared with a rolling baseline of "
                            f"{baseline:.2f}. Approximate Z-score: "
                            f"{z_score:.2f}."
                        ),
                    }
                )
                created += 1

    return created


def _detect_repeated_failures(df: pd.DataFrame) -> int:
    severe_df = df[df["is_severe"]].copy()

    if severe_df.empty:
        return 0

    grouped = (
        severe_df.groupby(
            [
                "dataset",
                "service",
                "severity",
                "message",
            ],
            dropna=False,
        )
        .agg(
            count=("id", "count"),
            first_seen=("timestamp", "min"),
            last_seen=("timestamp", "max"),
        )
        .reset_index()
    )

    created = 0

    for _, row in grouped.iterrows():
        count = int(row["count"])

        if count < 3:
            continue

        _save_anomaly(
            {
                "dataset": str(row["dataset"]),
                "service": str(row["service"]),
                "severity": str(row["severity"]),
                "anomaly_type": "repeated_failure",
                "time_bucket": row[
                    "first_seen"
                ].to_pydatetime(),
                "metric_name": "repeated_failure_count",
                "metric_value": float(count),
                "baseline_value": 1.0,
                "threshold_value": 3.0,
                "description": (
                    f"Repeated severe message occurred {count} times "
                    f"between {row['first_seen']} and "
                    f"{row['last_seen']}: "
                    f"{str(row['message'])[:150]}"
                ),
            }
        )
        created += 1

    return created


def _detect_unusual_service_activity(
    df: pd.DataFrame,
    rolling_window: int,
    z_score_threshold: float,
) -> int:
    hourly = (
        df.set_index("timestamp")
        .groupby(["dataset", "service"])
        .resample("1h")
        .size()
        .reset_index(name="count")
    )

    if hourly.empty:
        return 0

    created = 0

    for (dataset, service), group in hourly.groupby(
        ["dataset", "service"]
    ):
        group = group.sort_values("timestamp").copy()

        group["rolling_mean"] = (
            group["count"]
            .shift(1)
            .rolling(
                window=rolling_window,
                min_periods=1,
            )
            .mean()
        )

        group["rolling_std"] = (
            group["count"]
            .shift(1)
            .rolling(
                window=rolling_window,
                min_periods=2,
            )
            .std()
            .fillna(0)
        )

        for _, row in group.iterrows():
            observed = float(row["count"])
            baseline_value = row["rolling_mean"]

            if pd.isna(baseline_value):
                continue

            baseline = float(baseline_value)
            standard_deviation = float(row["rolling_std"])

            threshold = max(
                baseline
                + z_score_threshold * standard_deviation,
                baseline + 5,
                10.0,
            )

            if observed > threshold:
                _save_anomaly(
                    {
                        "dataset": str(dataset),
                        "service": str(service),
                        "severity": "INFO+",
                        "anomaly_type": (
                            "unusual_service_activity"
                        ),
                        "time_bucket": row[
                            "timestamp"
                        ].to_pydatetime(),
                        "metric_name": "logs_per_hour",
                        "metric_value": observed,
                        "baseline_value": round(
                            baseline,
                            2,
                        ),
                        "threshold_value": round(
                            threshold,
                            2,
                        ),
                        "description": (
                            f"{service} generated {int(observed)} logs "
                            f"in one hour compared with a rolling "
                            f"baseline of {baseline:.2f}."
                        ),
                    }
                )
                created += 1

    return created


def _save_anomaly(values: Dict[str, Any]) -> None:
    anomaly = Anomaly(**values)
    db.session.add(anomaly)
    db.session.flush()

    explanation = build_rule_based_explanation(anomaly)
    db.session.add(explanation)


def build_rule_based_explanation(
    anomaly: Anomaly
) -> AIExplanation:
    """
    Generate an interpretable explanation without calling an external LLM.

    The optional full AI/LLM integration remains appropriate for Report 6.
    """
    if anomaly.anomaly_type in {
        "rolling_error_spike",
        "repeated_failure",
    }:
        severity_assessment = "High"
        possible_root_cause = (
            "A recurring application failure, dependency outage, "
            "configuration issue, deployment problem, or resource "
            "constraint may be affecting the service."
        )
    else:
        severity_assessment = "Medium"
        possible_root_cause = (
            "The service may be experiencing a traffic burst, batch "
            "workload, retry loop, scheduled operation, or unusual "
            "application behavior."
        )

    recommended_action = (
        f"Review {anomaly.service} logs near "
        f"{anomaly.time_bucket}, inspect recurring messages, "
        "compare activity against the historical baseline, and "
        "check recent deployments, dependencies, and system resources."
    )

    return AIExplanation(
        anomaly_id=anomaly.id,
        summary=(
            f"Detected "
            f"{anomaly.anomaly_type.replace('_', ' ')} "
            f"for {anomaly.service}. {anomaly.description}"
        ),
        severity_assessment=severity_assessment,
        possible_root_cause=possible_root_cause,
        recommended_action=recommended_action,
        model_source="rule_based_statistical_explanation",
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _timestamped_dataframe(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> pd.DataFrame:
    df = logs_to_dataframe(filters)

    if df.empty:
        return df

    return df.dropna(subset=["timestamp"]).copy()


def _filtered_anomaly_count(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> int:
    query = Anomaly.query
    filters = filters or {}

    if filters.get("dataset"):
        query = query.filter(
            Anomaly.dataset == filters["dataset"]
        )

    if filters.get("service"):
        query = query.filter(
            Anomaly.service == filters["service"]
        )

    if filters.get("severity"):
        severity = filters["severity"].upper()

        query = query.filter(
            Anomaly.severity.ilike(
                f"%{severity}%"
            )
        )

    start = _parse_datetime(filters.get("start"))
    end = _parse_datetime(
        filters.get("end"),
        end_of_day=True,
    )

    if start:
        query = query.filter(
            Anomaly.time_bucket >= start
        )

    if end:
        query = query.filter(
            Anomaly.time_bucket <= end
        )

    return query.count()


def _parse_datetime(
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


def _percentage(
    numerator: int,
    denominator: int,
) -> float:
    if denominator == 0:
        return 0.0

    return round(
        numerator / denominator * 100,
        2,
    )


def _categorize_message(message: str) -> str:
    lowered = message.lower()

    categories = {
        "authentication": [
            "login",
            "password",
            "authentication",
            "unauthorized",
            "permission",
        ],
        "database": [
            "database",
            "sql",
            "connection",
            "timeout",
            "query",
        ],
        "network": [
            "network",
            "socket",
            "connection refused",
            "unreachable",
            "dns",
        ],
        "storage": [
            "disk",
            "hdfs",
            "block",
            "storage",
            "namenode",
            "datanode",
        ],
        "apache_worker": [
            "worker",
            "apache",
            "child process",
            "server reached",
        ],
        "resource": [
            "memory",
            "cpu",
            "resource",
            "capacity",
            "overflow",
        ],
    }

    for category, keywords in categories.items():
        if any(keyword in lowered for keyword in keywords):
            return category

    return "other_operational_issue"


def _mode(series: pd.Series) -> str:
    if series.empty:
        return "unknown"

    counts = Counter(
        series.dropna().astype(str).tolist()
    )

    return (
        counts.most_common(1)[0][0]
        if counts
        else "unknown"
    )


def _clean_value(
    value: Optional[str]
) -> Optional[str]:
    if value is None:
        return None

    cleaned = value.strip()

    return cleaned or None