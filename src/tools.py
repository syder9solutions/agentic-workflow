"""
Agent Tools (Agent-Computer Interface) with Poka-Yoke validation and structured error semantics.
Includes fault-injection simulator for testing resilient recovery.
"""
from typing import Any
from src.models import (
    ToolResult,
    ToolError,
    ErrorKind,
    ServiceName,
    RemediationActionInput,
    RemediationActionType,
    VerificationResult
)


class IncidentEnvironmentState:
    """Simulated production cluster environment with mutable state and fault injection."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.services = {
            ServiceName.CHECKOUT_SERVICE: {
                "version": "v2.4.1",
                "previous_stable_version": "v2.4.0",
                "replicas": 4,
                "error_rate": 18.5,  # Alert threshold is 2.0%
                "p95_latency_ms": 1420.0,
                "status": "degraded",
                "crash_looping": False,
                "root_cause": "bad_deployment_v2.4.1_memory_leak"
            },
            ServiceName.PAYMENT_GATEWAY: {
                "version": "v1.9.0",
                "previous_stable_version": "v1.8.9",
                "replicas": 6,
                "error_rate": 0.1,
                "p95_latency_ms": 180.0,
                "status": "healthy",
                "crash_looping": False,
                "root_cause": None
            }
        }
        # Injected faults for testing recovery
        self.transient_fault_counters: dict[str, int] = {}
        self.human_escalation_required = False


class SREToolbox:
    def __init__(self, state: IncidentEnvironmentState | None = None):
        self.state = state or IncidentEnvironmentState()

    def inject_transient_failure(self, tool_name: str, times: int = 1):
        """Forces the specified tool to fail N times with TRANSIENT error before succeeding."""
        self.state.transient_fault_counters[tool_name] = times

    def fetch_telemetry(self, service: ServiceName) -> ToolResult:
        """Fetches live telemetry: error rate, p95 latency, and CPU/memory utilization."""
        # Check transient fault injection
        if self.state.transient_fault_counters.get("fetch_telemetry", 0) > 0:
            self.state.transient_fault_counters["fetch_telemetry"] -= 1
            return ToolResult(
                ok=False,
                error=ToolError(
                    kind=ErrorKind.TRANSIENT,
                    message="Prometheus metrics API timeout (HTTP 504 Gateway Timeout)",
                    retry_after_ms=100
                )
            )

        if service not in self.state.services:
            return ToolResult(
                ok=False,
                error=ToolError(
                    kind=ErrorKind.PERMANENT,
                    message=f"Service '{service}' is not registered in service mesh.",
                    retry_after_ms=0
                )
            )

        data = self.state.services[service]
        return ToolResult(
            ok=True,
            value={
                "service": service,
                "error_rate_pct": data["error_rate"],
                "p95_latency_ms": data["p95_latency_ms"],
                "active_replicas": data["replicas"],
                "cluster_health": data["status"]
            }
        )

    def query_recent_deployments(self, service: ServiceName) -> ToolResult:
        """Retrieves recent git deployments, commits, and rollout timestamps."""
        data = self.state.services.get(service)
        if not data:
            return ToolResult(
                ok=False,
                error=ToolError(
                    kind=ErrorKind.PERMANENT,
                    message=f"Unknown service '{service}'"
                )
            )

        deployments = [
            {
                "version": data["version"],
                "deployed_minutes_ago": 14,
                "git_commit": "a8f9c2d",
                "author": "sre-ci-bot",
                "change_log": "Bump checkout worker concurrency pool to 64; add batch invoice pre-cache"
            },
            {
                "version": data["previous_stable_version"],
                "deployed_minutes_ago": 2880,
                "git_commit": "e4b110a",
                "author": "dev-lead",
                "change_log": "Production stable baseline v2.4.0"
            }
        ]
        return ToolResult(ok=True, value=deployments)

    def inspect_logs(self, service: ServiceName, lookback_minutes: int = 15) -> ToolResult:
        """Queries cluster log aggregator for error stacktraces and warnings."""
        if self.state.transient_fault_counters.get("inspect_logs", 0) > 0:
            self.state.transient_fault_counters["inspect_logs"] -= 1
            return ToolResult(
                ok=False,
                error=ToolError(
                    kind=ErrorKind.TRANSIENT,
                    message="Elasticsearch cluster rate limit exceeded (HTTP 429 Too Many Requests)",
                    retry_after_ms=150
                )
            )

        data = self.state.services.get(service)
        if not data:
            return ToolResult(ok=False, error=ToolError(kind=ErrorKind.PERMANENT, message="Service not found."))

        if data["status"] == "degraded":
            logs = [
                "ERROR: [checkout-worker-3] Memory limit exceeded: resident set size 1042MB > limit 1000MB",
                "CRITICAL: [kernel] Out of memory: Kill process 1421 (python) score 852 or sacrifice child",
                "ERROR: [ingress-nginx] Upstream connection failure to checkout-service:5000 (HTTP 502 Bad Gateway)",
                "WARN: [checkout-worker-1] Cascading retries detected; client backlog queue depth = 412"
            ]
        else:
            logs = ["INFO: Healthcheck probe 200 OK across all pods."]

        return ToolResult(ok=True, value={"service": service, "recent_log_entries": logs})

    def execute_remediation(self, action: RemediationActionInput) -> ToolResult:
        """Executes automated remediation: rollback, pod restart, or replica scale."""
        if self.state.human_escalation_required:
            return ToolResult(
                ok=False,
                error=ToolError(
                    kind=ErrorKind.REQUIRES_HUMAN,
                    message="Production security freeze in effect. Manual operator approval required.",
                    retry_after_ms=0
                )
            )

        srv = action.service
        if srv not in self.state.services:
            return ToolResult(
                ok=False,
                error=ToolError(kind=ErrorKind.PERMANENT, message="Invalid target service.")
            )

        # Apply action
        if action.action == RemediationActionType.ROLLBACK_DEPLOYMENT:
            target_v = action.target_version or self.state.services[srv]["previous_stable_version"]
            self.state.services[srv]["version"] = target_v
            self.state.services[srv]["status"] = "recovering"
            # Simulate health recovery post rollback
            self.state.services[srv]["error_rate"] = 0.08
            self.state.services[srv]["p95_latency_ms"] = 94.0
            return ToolResult(
                ok=True,
                value={
                    "status": "rolled_back",
                    "service": srv,
                    "active_version": target_v,
                    "reason": action.reason
                }
            )

        elif action.action == RemediationActionType.RESTART_PODS:
            # Temporary restart
            self.state.services[srv]["error_rate"] = 4.2
            return ToolResult(ok=True, value={"status": "restarted", "service": srv})

        elif action.action == RemediationActionType.SCALE_REPLICAS:
            count = action.replica_count or (self.state.services[srv]["replicas"] * 2)
            self.state.services[srv]["replicas"] = count
            return ToolResult(ok=True, value={"status": "scaled", "service": srv, "replicas": count})

        return ToolResult(ok=False, error=ToolError(kind=ErrorKind.PERMANENT, message="Unsupported action."))

    def verify_remediation(self, service: ServiceName) -> ToolResult:
        """
        Independent Verification Gate.
        Sends synthetic traffic and monitors SLA metrics to mathematically confirm recovery.
        """
        data = self.state.services.get(service)
        if not data:
            return ToolResult(ok=False, error=ToolError(kind=ErrorKind.PERMANENT, message="Service not found."))

        is_healthy = data["error_rate"] < 1.0 and data["p95_latency_ms"] < 300.0
        result = VerificationResult(
            service=service,
            is_healthy=is_healthy,
            current_error_rate=data["error_rate"],
            current_p95_latency_ms=data["p95_latency_ms"],
            active_pods=data["replicas"],
            message="Service recovered within SLA (error rate < 1%, p95 < 300ms)" if is_healthy else "Service remains degraded."
        )
        return ToolResult(ok=True, value=result.model_dump())
