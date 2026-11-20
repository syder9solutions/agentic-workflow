"""
Integration tests for human escalation guardrails and safety freezes.
"""
from src.models import (
    ServiceName,
    AlertSeverity,
    IncidentAlert
)
from src.tools import SREToolbox, IncidentEnvironmentState
from src.agent import SREIncidentAgent


def test_agent_escalates_on_production_freeze():
    alert = IncidentAlert(
        alert_id="ALRT-9102",
        service=ServiceName.CHECKOUT_SERVICE,
        severity=AlertSeverity.P1_CRITICAL,
        trigger_metric="error_rate_pct",
        metric_value=18.5,
        description="Checkout service degraded with elevated 5xx rate"
    )

    state = IncidentEnvironmentState()
    state.human_escalation_required = True
    toolbox = SREToolbox(state)

    agent = SREIncidentAgent(toolbox=toolbox)
    traj = agent.run(alert)

    assert traj.status == "ESCALATED"
    assert not traj.verification_passed
    assert "Escalated to human" in traj.summary_report
