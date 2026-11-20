"""
Unit tests for SRE Toolbox, structured errors, and verification gate.
"""
from src.models import (
    ServiceName,
    RemediationActionInput,
    RemediationActionType,
    ErrorKind
)
from src.tools import SREToolbox, IncidentEnvironmentState


def test_toolbox_telemetry_and_logs():
    toolbox = SREToolbox(IncidentEnvironmentState())
    
    # Telemetry
    tel = toolbox.fetch_telemetry(ServiceName.CHECKOUT_SERVICE)
    assert tel.ok
    assert tel.value["error_rate_pct"] > 0

    # Logs
    logs = toolbox.inspect_logs(ServiceName.CHECKOUT_SERVICE)
    assert logs.ok
    assert len(logs.value["recent_log_entries"]) > 0


def test_transient_error_injection():
    toolbox = SREToolbox(IncidentEnvironmentState())
    toolbox.inject_transient_failure("fetch_telemetry", times=1)

    # First call must fail with TRANSIENT error
    res1 = toolbox.fetch_telemetry(ServiceName.CHECKOUT_SERVICE)
    assert not res1.ok
    assert res1.error is not None
    assert res1.error.kind == ErrorKind.TRANSIENT
    assert res1.error.retry_after_ms > 0

    # Second call must succeed
    res2 = toolbox.fetch_telemetry(ServiceName.CHECKOUT_SERVICE)
    assert res2.ok


def test_remediation_and_verification():
    toolbox = SREToolbox(IncidentEnvironmentState())
    
    # Verification before remediation must show degraded
    v_before = toolbox.verify_remediation(ServiceName.CHECKOUT_SERVICE)
    assert v_before.ok
    assert not v_before.value["is_healthy"]

    # Remediate via rollback
    act = RemediationActionInput(
        service=ServiceName.CHECKOUT_SERVICE,
        action=RemediationActionType.ROLLBACK_DEPLOYMENT,
        target_version="v2.4.0",
        reason="Rollback memory leak"
    )
    rem = toolbox.execute_remediation(act)
    assert rem.ok
    assert rem.value["status"] == "rolled_back"

    # Verification after remediation must confirm healthy SLA
    v_after = toolbox.verify_remediation(ServiceName.CHECKOUT_SERVICE)
    assert v_after.ok
    assert v_after.value["is_healthy"]
    assert v_after.value["current_error_rate"] < 1.0
