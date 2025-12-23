import os

COST_PER_JOB = float(os.getenv("COST_PER_JOB", "0.0"))
CURRENCY = os.getenv("CURRENCY", "USD")