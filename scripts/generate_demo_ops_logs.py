"""Generate synthetic logs for local testing only. Use Loghub data for portfolio screenshots."""
from datetime import datetime, timedelta
from pathlib import Path
import random

services = ["auth-service", "payment-service", "api-gateway", "reporting-service"]
levels = ["INFO", "INFO", "INFO", "WARNING", "ERROR"]
messages = {
    "INFO": ["Request completed successfully", "User action completed", "Batch job completed"],
    "WARNING": ["Slow response time detected", "Retry attempt triggered", "Memory usage approaching threshold"],
    "ERROR": ["Database connection timeout", "Upstream service unavailable", "Invalid login attempt"],
}

start = datetime(2026, 6, 1, 8, 0, 0)
out = Path("data/demo/demo_ops_5000.log")
out.parent.mkdir(parents=True, exist_ok=True)

with out.open("w") as f:
    for i in range(5000):
        ts = start + timedelta(seconds=i * 30)
        service = random.choice(services)
        level = random.choice(levels)
        if 1800 < i < 1900 and service == "payment-service":
            level = "ERROR"
        f.write(f"{ts:%Y-%m-%d %H:%M:%S} {level} {service} {random.choice(messages[level])}\n")
print(f"Generated {out}")
