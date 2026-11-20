"""
Domain models, Poka-Yoke tool contracts, and structured error schemas.
"""
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ErrorKind(str, Enum):
    TRANSIENT = "TRANSIENT"            # Upstream 503, network glitch, lock contention -> Safe to retry
    PERMANENT = "PERMANENT"            # Invalid argument, resource not found -> Do not retry
    REQUIRES_HUMAN = "REQUIRES_HUMAN"  # Privilege required, production wipe confirmation -> Escalate


class ToolError(BaseModel):
    kind: ErrorKind
    message: str
    retry_after_ms: int = 0
    details: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    ok: bool
    value: Any = None
    error: ToolError | None = None


# --- Poka-Yoke Tool Input Schemas ---

class ServiceName(str, Enum):
    CHECKOUT_SERVICE = "checkout-service"
    PAYMENT_GATEWAY = "payment-gateway"
    AUTH_SERVICE = "auth-service"
    CATALOG_API = "catalog-api"


class AlertSeverity(str, Enum):
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"


class IncidentAlert(BaseModel):
    alert_id: str = Field(..., pattern=r"^ALRT-[0-9]{4,}$")
    service: ServiceName
    severity: AlertSeverity
    trigger_metric: str
    metric_value: float
    description: str


class RemediationActionType(str, Enum):
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    RESTART_PODS = "restart_pods"
    SCALE_REPLICAS = "scale_replicas"
    FLUSH_CIRCUIT_BREAKER = "flush_circuit_breaker"


class RemediationActionInput(BaseModel):
    service: ServiceName
    action: RemediationActionType
    reason: str = Field(..., min_length=10)
    target_version: str | None = Field(default=None, pattern=r"^v[0-9]+\.[0-9]+\.[0-9]+$")
    replica_count: int | None = Field(default=None, ge=1, le=50)


class VerificationResult(BaseModel):
    service: ServiceName
    is_healthy: bool
    current_error_rate: float
    current_p95_latency_ms: float
    active_pods: int
    message: str
