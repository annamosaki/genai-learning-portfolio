"""Human-in-the-loop approval gates for Agent Desk."""

import asyncio
from typing import Dict

from .config import settings
from .events import EventType, event_bus
from .models import ApprovalDecision, ApprovalGate, ApprovalRequest


class ApprovalManager:
    """Manages approval gates and human-in-the-loop decisions."""

    def __init__(self) -> None:
        self._pending_approvals: Dict[str, asyncio.Event] = {}
        self._approval_results: Dict[str, ApprovalRequest] = {}

    async def require_approval(
        self,
        run_id: str,
        gate_type: str,
        description: str,
        content: str,
    ) -> ApprovalRequest:
        """Require approval for a gate and wait for human decision."""
        gate_id = f"{run_id}_{gate_type}_{len(self._pending_approvals)}"

        ApprovalGate(
            id=gate_id,
            type=gate_type,  # type: ignore[arg-type]
            description=description,
            content=content,
        )

        await event_bus.emit(
            run_id=run_id,
            event_type=EventType.APPROVAL_REQUIRED,
            data={
                "gate_id": gate_id,
                "type": gate_type,
                "description": description,
                "content": content,
            },
        )

        approval_event = asyncio.Event()
        self._pending_approvals[gate_id] = approval_event

        timeout = float(settings.approval_timeout_seconds)
        # Lambda: also honour AUTO_APPROVE_ON_TIMEOUT / shorter timeouts from env
        import os

        if os.environ.get("AUTO_APPROVE_ON_TIMEOUT", "").lower() in ("1", "true", "yes"):
            settings.auto_approve_on_timeout = True
        if os.environ.get("APPROVAL_TIMEOUT_SECONDS"):
            try:
                timeout = float(os.environ["APPROVAL_TIMEOUT_SECONDS"])
            except ValueError:
                pass

        try:
            from .serverless_runtime import is_serverless, run_store

            if is_serverless() and run_store.enabled:
                # Poll DynamoDB so /approve on another invocation can resolve this gate.
                deadline = asyncio.get_event_loop().time() + (timeout if timeout > 0 else 1e9)
                while asyncio.get_event_loop().time() < deadline:
                    if approval_event.is_set():
                        break
                    remote = run_store.get(f"desk#{run_id}", f"approval#{gate_id}")
                    if remote:
                        decision_raw = str(remote.get("decision", "approve")).lower()
                        try:
                            decision = ApprovalDecision(decision_raw)
                        except ValueError:
                            decision = ApprovalDecision.APPROVE
                        self._approval_results[gate_id] = ApprovalRequest(
                            tool_call_id=gate_id,
                            decision=decision,
                            message=remote.get("message"),
                            override_args=remote.get("override_args"),
                        )
                        approval_event.set()
                        break
                    await asyncio.sleep(0.4)
                if not approval_event.is_set():
                    raise asyncio.TimeoutError()
            elif timeout > 0:
                await asyncio.wait_for(approval_event.wait(), timeout=timeout)
            else:
                await approval_event.wait()
        except asyncio.TimeoutError:
            if settings.auto_approve_on_timeout:
                result = ApprovalRequest(
                    tool_call_id=gate_id,
                    decision=ApprovalDecision.APPROVE,
                    message="Auto-approved after timeout",
                )
                self._approval_results[gate_id] = result
                await event_bus.emit(
                    run_id=run_id,
                    event_type=EventType.APPROVAL_RESOLVED,
                    data={
                        "gate_id": gate_id,
                        "decision": "approve",
                        "auto": True,
                        "message": "Auto-approved after timeout",
                    },
                )
                self._pending_approvals.pop(gate_id, None)
                return result

            # Live default: treat timeout as deny so we don't silently proceed
            result = ApprovalRequest(
                tool_call_id=gate_id,
                decision=ApprovalDecision.DENY,
                message="Approval timed out without response",
            )
            self._approval_results[gate_id] = result
            await event_bus.emit(
                run_id=run_id,
                event_type=EventType.APPROVAL_RESOLVED,
                data={
                    "gate_id": gate_id,
                    "decision": "deny",
                    "auto": True,
                    "message": "Approval timed out without response",
                },
            )
            self._pending_approvals.pop(gate_id, None)
            return result

        result = self._approval_results.get(gate_id)
        if result is None:
            result = ApprovalRequest(
                tool_call_id=gate_id,
                decision=ApprovalDecision.APPROVE,
            )

        self._pending_approvals.pop(gate_id, None)
        self._approval_results.pop(gate_id, None)

        await event_bus.emit(
            run_id=run_id,
            event_type=EventType.APPROVAL_RESOLVED,
            data={
                "gate_id": gate_id,
                "decision": result.decision.value,
                "message": result.message,
            },
        )
        return result

    def resolve_approval(self, gate_id: str, approval: ApprovalRequest) -> bool:
        """Resolve a pending approval."""
        if gate_id not in self._pending_approvals:
            return False
        self._approval_results[gate_id] = approval
        self._pending_approvals[gate_id].set()
        return True

    def get_pending_approvals(self) -> Dict[str, str]:
        return {gate_id: "pending" for gate_id in self._pending_approvals.keys()}


approval_manager = ApprovalManager()
