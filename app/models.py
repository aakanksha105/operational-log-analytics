from datetime import datetime
from app.extensions import db


class UploadBatch(db.Model):
    __tablename__ = "upload_batches"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    dataset_name = db.Column(db.String(120), nullable=True)
    parser_used = db.Column(db.String(60), nullable=False)
    records_inserted = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LogRecord(db.Model):
    __tablename__ = "log_records"

    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.Integer, db.ForeignKey("upload_batches.id"), nullable=True, index=True)
    dataset = db.Column(db.String(120), index=True)
    timestamp = db.Column(db.DateTime, index=True)
    severity = db.Column(db.String(30), index=True)
    service = db.Column(db.String(120), index=True)
    component = db.Column(db.String(160), index=True)
    event_type = db.Column(db.String(120), index=True)
    message = db.Column(db.Text)
    raw_log = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "dataset": self.dataset,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "severity": self.severity,
            "service": self.service,
            "component": self.component,
            "event_type": self.event_type,
            "message": self.message,
            "raw_log": self.raw_log,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Anomaly(db.Model):
    __tablename__ = "anomalies"

    id = db.Column(db.Integer, primary_key=True)
    dataset = db.Column(db.String(120), index=True)
    service = db.Column(db.String(120), index=True)
    severity = db.Column(db.String(30), index=True)
    anomaly_type = db.Column(db.String(120), index=True)
    time_bucket = db.Column(db.DateTime, index=True)
    metric_name = db.Column(db.String(120))
    metric_value = db.Column(db.Float)
    baseline_value = db.Column(db.Float)
    threshold_value = db.Column(db.Float)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    explanations = db.relationship("AIExplanation", backref="anomaly", lazy=True, cascade="all, delete-orphan")

    def to_dict(self, include_explanation=True):
        data = {
            "id": self.id,
            "dataset": self.dataset,
            "service": self.service,
            "severity": self.severity,
            "anomaly_type": self.anomaly_type,
            "time_bucket": self.time_bucket.isoformat() if self.time_bucket else None,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "baseline_value": self.baseline_value,
            "threshold_value": self.threshold_value,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_explanation:
            data["explanations"] = [exp.to_dict() for exp in self.explanations]
        return data


class AIExplanation(db.Model):
    __tablename__ = "ai_explanations"

    id = db.Column(db.Integer, primary_key=True)
    anomaly_id = db.Column(db.Integer, db.ForeignKey("anomalies.id"), nullable=False, index=True)
    summary = db.Column(db.Text)
    severity_assessment = db.Column(db.String(60))
    possible_root_cause = db.Column(db.Text)
    recommended_action = db.Column(db.Text)
    model_source = db.Column(db.String(60), default="rule_based")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "anomaly_id": self.anomaly_id,
            "summary": self.summary,
            "severity_assessment": self.severity_assessment,
            "possible_root_cause": self.possible_root_cause,
            "recommended_action": self.recommended_action,
            "model_source": self.model_source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
