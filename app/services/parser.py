import re
from datetime import datetime
from typing import Dict, Iterable, List, Optional

APACHE_PATTERN = re.compile(
    r"^\[(?P<ts>[^\]]+)\]\s+\[(?P<severity>[^\]]+)\]\s+(?P<message>.*)$"
)

HDFS_PATTERN = re.compile(
    r"^(?P<date>\d{6})\s+(?P<time>\d{6})\s+(?P<pid>\d+)\s+(?P<severity>\w+)\s+(?P<component>[^:]+):\s+(?P<message>.*)$"
)

GENERIC_PATTERN = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+(?P<severity>\w+)\s+(?P<service>[\w.$-]+)\s+(?P<message>.*)$"
)

SEVERITY_MAP = {
    "emerg": "CRITICAL",
    "alert": "CRITICAL",
    "crit": "CRITICAL",
    "critical": "CRITICAL",
    "error": "ERROR",
    "err": "ERROR",
    "warn": "WARNING",
    "warning": "WARNING",
    "notice": "INFO",
    "info": "INFO",
    "debug": "DEBUG",
}


def normalize_severity(level: str) -> str:
    return SEVERITY_MAP.get((level or "INFO").strip().lower(), (level or "INFO").upper())


def classify_event(message: str) -> str:
    text = (message or "").lower()
    if any(word in text for word in ["error", "failed", "failure", "exception", "timeout", "unavailable"]):
        return "failure"
    if any(word in text for word in ["terminating", "shutdown", "closed", "exit"]):
        return "termination"
    if any(word in text for word in ["received", "receiving", "accepted"]):
        return "data_transfer"
    if any(word in text for word in ["addstoredblock", "allocateblock", "blockmap"]):
        return "block_operation"
    return "normal_activity"


def parse_apache(line: str, dataset: str) -> Optional[Dict]:
    match = APACHE_PATTERN.match(line.strip())
    if not match:
        return None
    raw_ts = match.group("ts")
    timestamp = datetime.strptime(raw_ts, "%a %b %d %H:%M:%S %Y")
    severity = normalize_severity(match.group("severity"))
    message = match.group("message").strip()
    return {
        "dataset": dataset,
        "timestamp": timestamp,
        "severity": severity,
        "service": "apache-server",
        "component": extract_apache_component(message),
        "event_type": classify_event(message),
        "message": message,
        "raw_log": line.strip(),
    }


def extract_apache_component(message: str) -> str:
    if not message:
        return "apache"
    token = message.split()[0]
    return token.replace("()", "").replace(":", "")[:150]


def parse_hdfs(line: str, dataset: str) -> Optional[Dict]:
    match = HDFS_PATTERN.match(line.strip())
    if not match:
        return None
    timestamp = datetime.strptime(match.group("date") + match.group("time"), "%y%m%d%H%M%S")
    severity = normalize_severity(match.group("severity"))
    component = match.group("component").strip()
    message = match.group("message").strip()
    service = component.split("$")[0].split(".")[-1] if component else "hdfs"
    return {
        "dataset": dataset,
        "timestamp": timestamp,
        "severity": severity,
        "service": f"hdfs-{service.lower()}",
        "component": component,
        "event_type": classify_event(message),
        "message": message,
        "raw_log": line.strip(),
    }


def parse_generic(line: str, dataset: str) -> Optional[Dict]:
    match = GENERIC_PATTERN.match(line.strip())
    if not match:
        return None
    timestamp = datetime.strptime(match.group("ts"), "%Y-%m-%d %H:%M:%S")
    message = match.group("message").strip()
    return {
        "dataset": dataset,
        "timestamp": timestamp,
        "severity": normalize_severity(match.group("severity")),
        "service": match.group("service"),
        "component": match.group("service"),
        "event_type": classify_event(message),
        "message": message,
        "raw_log": line.strip(),
    }


def parse_line(line: str, dataset: str = "unknown") -> Optional[Dict]:
    if not line or not line.strip():
        return None
    for parser in (parse_apache, parse_hdfs, parse_generic):
        parsed = parser(line, dataset)
        if parsed:
            return parsed
    return {
        "dataset": dataset,
        "timestamp": None,
        "severity": "UNKNOWN",
        "service": "unknown",
        "component": "unknown",
        "event_type": "unparsed",
        "message": line.strip(),
        "raw_log": line.strip(),
    }


def parse_lines(lines: Iterable[str], dataset: str = "unknown") -> List[Dict]:
    return [parsed for line in lines if (parsed := parse_line(line, dataset))]


def infer_dataset_name(filename: str) -> str:
    lower = (filename or "").lower()
    if "apache" in lower:
        return "Loghub-Apache"
    if "hdfs" in lower:
        return "Loghub-HDFS"
    return "Operational-Logs"
