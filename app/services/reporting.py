from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.services.analytics import (
    daily_analysis,
    get_kpis,
    root_cause_patterns,
    service_comparison,
    weekly_analysis,
)


def build_daily_report(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> Dict[str, Any]:
    return {
        "report_type": "daily",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": filters or {},
        "kpis": get_kpis(filters),
        "daily_trend": daily_analysis(filters),
        "service_comparison": service_comparison(filters),
        "root_cause_patterns": root_cause_patterns(filters),
    }


def build_weekly_report(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> Dict[str, Any]:
    return {
        "report_type": "weekly",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": filters or {},
        "kpis": get_kpis(filters),
        "weekly_trend": weekly_analysis(filters),
        "service_comparison": service_comparison(filters),
        "root_cause_patterns": root_cause_patterns(filters),
    }


def build_summary_report(
    filters: Optional[Dict[str, Optional[str]]] = None
) -> Dict[str, Any]:
    return {
        "report_type": "summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "filters": filters or {},
        "kpis": get_kpis(filters),
        "service_comparison": service_comparison(filters),
        "root_cause_patterns": root_cause_patterns(filters),
    }