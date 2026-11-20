"""
FastAPI Application for SRE Incident Remediation Agent (`OpsRescue`).
Exposes endpoints for triggering incident remediations, inspecting agent trajectories,
and executing the automated trajectory evaluation suite.
"""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.models import (
    IncidentAlert,
    ServiceName,
    AlertSeverity
)
from src.tools import SREToolbox, IncidentEnvironmentState
from src.agent import SREIncidentAgent, AgentTrajectory
from evals.trajectory_eval import run_trajectory_benchmark

app = FastAPI(
    title="Autonomous SRE Incident Remediation Agent",
    description="Production agentic workflow with ReAct loop, retry budgets, poka-yoke schemas, and verification gates.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class TriggerIncidentRequest(BaseModel):
    service: ServiceName = Field(ServiceName.CHECKOUT_SERVICE)
    severity: AlertSeverity = Field(AlertSeverity.P1_CRITICAL)
    trigger_metric: str = Field("error_rate_pct")
    metric_value: float = Field(18.5)
    description: str = Field("Spike in 5xx HTTP errors following recent release rollout.")
    inject_fault: bool = Field(False, description="Simulate transient upstream API failures")
    simulate_production_freeze: bool = Field(False, description="Simulate human privilege freeze")


@app.get("/", response_class=HTMLResponse)
def index():
    html_file = WEB_DIR / "index.html"
    if not html_file.exists():
        return HTMLResponse("<h1>Agent UI loading...</h1>")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@app.post("/api/incident/trigger", response_model=AgentTrajectory)
def trigger_incident(req: TriggerIncidentRequest):
    state = IncidentEnvironmentState()
    if req.simulate_production_freeze:
        state.human_escalation_required = True

    toolbox = SREToolbox(state)
    if req.inject_fault:
        toolbox.inject_transient_failure("fetch_telemetry", times=1)
        toolbox.inject_transient_failure("inspect_logs", times=1)

    agent = SREIncidentAgent(toolbox=toolbox)
    alert = IncidentAlert(
        alert_id="ALRT-9102",
        service=req.service,
        severity=req.severity,
        trigger_metric=req.trigger_metric,
        metric_value=req.metric_value,
        description=req.description
    )

    trajectory = agent.run(alert)
    return trajectory


@app.post("/api/eval/trajectory")
def run_eval():
    report = run_trajectory_benchmark()
    return report


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "agent": "OpsRescue-v1",
        "supported_services": [s.value for s in ServiceName]
    }
