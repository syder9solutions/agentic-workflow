"""
Integration tests for the complete Agentic Workflow (Think-Act-Observe loop).
"""
from src.models import (
    ServiceName,
    AlertSeverity,
    IncidentAlert
)
from src.tools import SREToolbox, IncidentEnvironmentState
from src.agent import SREIncidentAgent


def test_agent_resolves_incident_end_to_end():
    alert = IncidentAlert(
        alert_id="ALRT-9102",
        service=ServiceName.CHECKOUT_SERVICE,
        severity=AlertSeverity.P1_CRITICAL,
        trigger_metric="error_rate_pct",
        metric_value=18.5,
        description="Checkout service degraded with elevated 5xx rate"
    )

    toolbox = SREToolbox(IncidentEnvironmentState())
    agent = SREIncidentAgent(toolbox=toolbox)
    traj = agent.run(alert)

    # Assertions on successful resolution
    assert traj.status == "RESOLVED"
    assert traj.verification_passed
    assert traj.total_tool_calls >= 4
    assert len(traj.steps) >= 4

    # Verify tool execution order: telemetry -> logs -> deployments -> remediation -> verification
    tools_called = [s.action_tool for s in traj.steps]
    assert tools_called == [
        "fetch_telemetry",
        "inspect_logs",
        "query_recent_deployments",
        "execute_remediation",
        "verify_remediation"
    ]
    assert "Incident ALRT-9102 successfully mitigated" in traj.summary_report
