"""
Integration tests for transient error recovery and retry budgets.
"""
from src.models import (
    ServiceName,
    AlertSeverity,
    IncidentAlert
)
from src.tools import SREToolbox, IncidentEnvironmentState
from src.agent import SREIncidentAgent


def test_agent_recovers_from_injected_transient_failures():
    alert = IncidentAlert(
        alert_id="ALRT-9102",
        service=ServiceName.CHECKOUT_SERVICE,
        severity=AlertSeverity.P1_CRITICAL,
        trigger_metric="error_rate_pct",
        metric_value=18.5,
        description="Checkout service degraded with elevated 5xx rate"
    )

    state = IncidentEnvironmentState()
    toolbox = SREToolbox(state)
    # Inject 1 transient failure on telemetry and 1 on logs
    toolbox.inject_transient_failure("fetch_telemetry", times=1)
    toolbox.inject_transient_failure("inspect_logs", times=1)

    agent = SREIncidentAgent(toolbox=toolbox, transient_retry_budget=3)
    traj = agent.run(alert)

    assert traj.status == "RESOLVED"
    assert traj.verification_passed
    assert traj.transient_retries_performed == 2

    # Check recovery step recorded
    recovery_steps = [s for s in traj.steps if s.error_recovery]
    assert len(recovery_steps) == 2
