"""
Event Status Lifecycle & State Machine (Phase 3 - Step 6)
==========================================================
Enforces the mandatory defect lifecycle state transitions:

  UNVERIFIED
       ↓
   CONFIRMED
       ↓
  UNDER REPAIR
       ↓
   RESOLVED

Also allows:
   DISMISSED (from UNVERIFIED, CONFIRMED, or UNDER REPAIR)

Reopening:
   RESOLVED -> UNVERIFIED (via post-repair re-detection watchdog)
   DISMISSED -> UNVERIFIED (via audit review)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from sqlmodel import Session, select

logger = logging.getLogger("services.state_machine")


class EventStatus(str, Enum):
    UNVERIFIED = "unverified"
    CONFIRMED = "confirmed"
    UNDER_REPAIR = "under_repair"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


# Canonical status normalization map
STATUS_ALIAS_MAP: Dict[str, EventStatus] = {
    "unverified": EventStatus.UNVERIFIED,
    "ai_detected": EventStatus.UNVERIFIED,
    "active": EventStatus.UNVERIFIED,
    "pending": EventStatus.UNVERIFIED,
    "new": EventStatus.UNVERIFIED,
    "confirmed": EventStatus.CONFIRMED,
    "under_repair": EventStatus.UNDER_REPAIR,
    "under repair": EventStatus.UNDER_REPAIR,
    "assigned": EventStatus.UNDER_REPAIR,
    "resolved": EventStatus.RESOLVED,
    "closed": EventStatus.RESOLVED,
    "dismissed": EventStatus.DISMISSED,
    "rejected": EventStatus.DISMISSED,
}

# Permitted state transition rules
VALID_TRANSITIONS: Dict[EventStatus, Set[EventStatus]] = {
    EventStatus.UNVERIFIED: {EventStatus.CONFIRMED, EventStatus.DISMISSED},
    EventStatus.CONFIRMED: {EventStatus.UNDER_REPAIR, EventStatus.DISMISSED},
    EventStatus.UNDER_REPAIR: {EventStatus.RESOLVED, EventStatus.DISMISSED},
    EventStatus.RESOLVED: {EventStatus.UNVERIFIED},  # Watchdog re-detection
    EventStatus.DISMISSED: {EventStatus.UNVERIFIED},  # Reopen on audit
}


def normalize_status(raw: Union[str, EventStatus]) -> EventStatus:
    """Normalizes any casing or spacing representation into canonical EventStatus."""
    if isinstance(raw, EventStatus):
        return raw
    cleaned = str(raw).strip().lower()
    if cleaned in STATUS_ALIAS_MAP:
        return STATUS_ALIAS_MAP[cleaned]
    # Fallback attempt
    cleaned_snake = cleaned.replace(" ", "_")
    if cleaned_snake in STATUS_ALIAS_MAP:
        return STATUS_ALIAS_MAP[cleaned_snake]
    raise ValueError(f"Unknown status '{raw}'. Permitted statuses: {[s.value for s in EventStatus]}")


def get_allowed_transitions(current_status: Union[str, EventStatus]) -> List[str]:
    """Returns the list of valid target statuses from current status."""
    norm = normalize_status(current_status) if isinstance(current_status, str) else current_status
    allowed = VALID_TRANSITIONS.get(norm, set())
    return [s.value for s in allowed]


def validate_transition(current_status: str, target_status: str) -> Tuple[bool, Optional[str]]:
    """
    Validates whether moving from current_status to target_status complies with the state machine.
    Returns (True, None) if valid, or (False, error_message) if invalid.
    """
    try:
        cur_norm = normalize_status(current_status)
        tgt_norm = normalize_status(target_status)
    except ValueError as e:
        return False, str(e)

    if cur_norm == tgt_norm:
        return True, f"Event is already in status '{tgt_norm.value}'."

    allowed = VALID_TRANSITIONS.get(cur_norm, set())
    if tgt_norm not in allowed:
        return False, (
            f"Invalid transition from '{cur_norm.value}' to '{tgt_norm.value}'. "
            f"Permitted transitions from '{cur_norm.value}': {[s.value for s in allowed]}."
        )

    return True, None


def execute_status_transition(
    event_id: str,
    target_status: str,
    session: Session,
    actor: str = "OPERATOR_COMMAND_CENTER",
    reason: Optional[str] = None,
    work_order_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes a validated status transition on an IngestedEvent record in the database.
    Updates the status and appends to the audit history in metadata_json.
    """
    from ..models.ingested_event import IngestedEvent

    # Find the event
    statement = select(IngestedEvent).where(
        (IngestedEvent.event_id == event_id) | (IngestedEvent.idempotency_key == event_id)
    )
    event = session.exec(statement).first()
    if not event:
        raise ValueError(f"Event with ID '{event_id}' not found.")

    current_status = event.status or "unverified"
    is_valid, err = validate_transition(current_status, target_status)
    if not is_valid:
        raise ValueError(err)

    norm_target = normalize_status(target_status)
    old_status = normalize_status(current_status).value

    # Update status
    event.status = norm_target.value

    # Append audit trail in metadata_json
    metadata = event.get_metadata()
    if "lifecycle_history" not in metadata:
        metadata["lifecycle_history"] = []

    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from_status": old_status,
        "to_status": norm_target.value,
        "actor": actor,
        "reason": reason or f"State transitioned to {norm_target.value}",
    }
    if work_order_id:
        audit_entry["work_order_id"] = work_order_id

    metadata["lifecycle_history"].append(audit_entry)
    metadata["last_updated_at"] = datetime.now(timezone.utc).isoformat()
    metadata["last_actor"] = actor

    import json
    event.metadata_json = json.dumps(metadata)
    session.add(event)
    session.commit()
    session.refresh(event)

    return {
        "eventId": event.event_id,
        "previousStatus": old_status,
        "newStatus": norm_target.value,
        "allowedNextTransitions": get_allowed_transitions(norm_target),
        "auditEntry": audit_entry,
    }
