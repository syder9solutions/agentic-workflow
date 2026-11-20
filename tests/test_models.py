"""
Unit tests for Poka-Yoke tool schemas and model validation.
"""
import pytest
from pydantic import ValidationError
from src.models import (
    ServiceName,
    AlertSeverity,
    IncidentAlert,
    RemediationActionInput,
    RemediationActionType
)


def test_incident_alert_validation():
    alert = IncidentAlert(
        alert_id="ALRT-1001",
        service=ServiceName.CHECKOUT_SERVICE,
        severity=AlertSeverity.P1_CRITICAL,
        trigger_metric="error_rate",
        metric_value=12.5,
        description="Checkout latency alert"
    )
    assert alert.alert_id == "ALRT-1001"

    # Invalid alert_id pattern must raise ValidationError
    with pytest.raises(ValidationError):
        IncidentAlert(
            alert_id="INVALID_ID",
            service=ServiceName.CHECKOUT_SERVICE,
            severity=AlertSeverity.P1_CRITICAL,
            trigger_metric="error_rate",
            metric_value=12.5,
            description="Checkout latency alert"
        )


def test_remediation_action_poka_yoke():
    action = RemediationActionInput(
        service=ServiceName.CHECKOUT_SERVICE,
        action=RemediationActionType.ROLLBACK_DEPLOYMENT,
        target_version="v2.4.0",
        reason="Rollback due to high error rate"
    )
    assert action.action == RemediationActionType.ROLLBACK_DEPLOYMENT

    # Invalid version pattern must be rejected
    with pytest.raises(ValidationError):
        RemediationActionInput(
            service=ServiceName.CHECKOUT_SERVICE,
            action=RemediationActionType.ROLLBACK_DEPLOYMENT,
            target_version="non-semver-version",
            reason="Rollback reason"
        )
