from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import indicators, filings, financials, summary, pipeline

app = FastAPI(title="SME Indicators API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:4173",
        "http://98.81.94.194",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(indicators.router, prefix="/api")
app.include_router(filings.router, prefix="/api")
app.include_router(financials.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(pipeline.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
