import sys

from fastapi import FastAPI

from dataset_manager import load_dataset

from routers.negotiation_router import router, set_dataset


# =====================================================
# WINDOWS UTF-8 SUPPORT
# =====================================================

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace"
        )
        sys.stderr.reconfigure(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        pass


# =====================================================
# FASTAPI APPLICATION
# =====================================================

app = FastAPI(
    title="Real Estate Negotiation Platform",
    description=(
        "AI-Driven Multi-Agent Negotiation Training & "
        "Simulation Platform with Interactive Human Practice Mode"
    ),
    version="1.3.0"
)


# =====================================================
# LOAD DATASET
# =====================================================

try:
    dataset = load_dataset("dataset_real.csv")

    if dataset is None:
        dataset = []

    print(
        f"Dataset loaded successfully: {len(dataset)} properties"
    )

except Exception as error:
    print(
        "Dataset loading error:",
        error
    )
    dataset = []


# =====================================================
# PASS DATASET TO NEGOTIATION ROUTER
# =====================================================

set_dataset(dataset)


# =====================================================
# ROOT
# =====================================================

@app.get("/")
def home():
    return {
        "message": (
            "Real Estate Negotiation Platform API "
            "is running"
        ),
        "docs": "/docs",
        "features": [
            "Scenario-based property filtering",
            "AI vs AI Multi-Agent Simulation",
            "Human vs AI Interactive Practice Mode",
            "Deadlock Detection"
        ]
    }


# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
def health():

    if dataset is None:
        dataset_loaded = False
        property_count = 0

    elif hasattr(dataset, "empty"):
        dataset_loaded = not dataset.empty
        property_count = len(dataset)

    else:
        dataset_loaded = len(dataset) > 0
        property_count = len(dataset)

    return {
        "status": "running",
        "dataset_loaded": dataset_loaded,
        "property_count": property_count
    }


# =====================================================
# INCLUDE NEGOTIATION ROUTER
# =====================================================

app.include_router(router)