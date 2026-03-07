"""
Database table schema definitions for 3CX Professional.

Verified against 3CX v20.0.8 Professional database backup.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum


class CallStatus(str, Enum):
    """Call status values (from is_answered field)."""
    ANSWERED = "t"
    NOT_ANSWERED = "f"


class CallDirection(str, Enum):
    """Call direction (from cl_party_info.is_inbound)."""
    INBOUND = "t"
    OUTBOUND = "f"


class DnType(str, Enum):
    """DN type codes from cl_participants.dn_type."""
    EXTENSION = "0"
    EXTERNAL_LINE = "1"
    RING_GROUP = "2"
    VOICEMAIL = "5"
    INBOUND_ROUTING = "13"


class SegmentType(str, Enum):
    """Segment type codes from cl_segments.type."""
    RINGING = "1"
    CONNECTED = "2"


@dataclass
class CallRecord:
    """Call record from cl_calls table."""
    id: int
    start_time: datetime
    end_time: Optional[datetime]
    is_answered: bool
    ringing_dur: str  # INTERVAL type
    talking_dur: str  # INTERVAL type
    q_wait_dur: str  # INTERVAL type
    call_history_id: Optional[str]  # UUID
    duplicated: bool
    migrated: bool

    @property
    def duration_seconds(self) -> Optional[int]:
        """Get talking duration in seconds."""
        if self.talking_dur:
            h, m, s = self.talking_dur.split(":")
            return int(h) * 3600 + int(m) * 60 + int(float(s))
        return None


@dataclass
class Participant:
    """Participant record from cl_participants table."""
    id: int
    dn_type: int  # 0=extension, 1=external, 2=ring_group, 5=voicemail, 13=inbound
    dn: str
    caller_number: str
    display_name: str
    dn_class: int
    firstlastname: str
    did_number: str
    crm_contact: str


@dataclass
class Segment:
    """Call segment from cl_segments table."""
    id: int
    call_id: int
    seq_order: int
    seq_group: int
    src_part_id: int
    dst_part_id: int
    start_time: datetime
    end_time: datetime
    type: int  # 1=ringing, 2=connected
    action_id: int
    action_party_id: Optional[int]
    call_history_id: Optional[str]


@dataclass
class PartyInfo:
    """Party info from cl_party_info table."""
    id: int
    call_id: int
    info_id: int
    role: int
    is_inbound: bool
    end_status: int
    forward_reason: int
    failure_reason: int
    start_time: datetime
    answer_time: Optional[datetime]
    end_time: datetime
    billing_code: Optional[str]
    billing_ratename: Optional[str]
    billing_rate: Optional[int]
    billing_cost: Optional[Decimal]
    billing_duration: str  # INTERVAL
    recording_url: Optional[str]


@dataclass
class CdrOutput:
    """CDR record from cdroutput table."""
    cdr_id: str  # UUID
    call_history_id: str  # UUID
    source_participant_id: str  # UUID
    source_entity_type: str
    source_dn_number: str
    source_dn_type: str
    source_dn_name: str
    source_participant_name: str
    source_participant_phone_number: str
    source_participant_is_incoming: bool
    destination_participant_id: str  # UUID
    destination_entity_type: str
    destination_dn_number: str
    destination_dn_type: str
    destination_dn_name: str
    destination_participant_name: str
    creation_method: str
    termination_reason: str
    cdr_started_at: datetime
    cdr_ended_at: datetime
    cdr_answered_at: Optional[datetime]


@dataclass
class Recording:
    """Recording record from recordings table."""
    id_recording: int
    cl_participants_id: Optional[int]
    recording_url: str
    start_time: datetime
    end_time: datetime
    transcription: Optional[str]
    call_type: int  # 1=inbound, 2=outbound
    sentiment_score: Optional[int]  # 1-5
    summary: Optional[str]
    cdr_id: str  # UUID
    transcribed: bool
    queued_dn: Optional[str]


@dataclass
class Voicemail:
    """Voicemail record from s_voicemail table."""
    idcallcent_queuecalls: int
    wav_file: str
    callee: str
    caller: str
    caller_name: str
    duration: int  # seconds
    created_time: str  # Unix timestamp
    heard: bool
    transcription: Optional[str]
    sentiment_score: Optional[int]


@dataclass
class QueueStats:
    """Queue statistics from callcent_queuecalls table."""
    idcallcent_queuecalls: int
    q_num: str  # Queue number
    time_start: datetime
    time_end: datetime
    ts_waiting: str  # INTERVAL
    ts_polling: str  # INTERVAL
    ts_servicing: str  # INTERVAL
    count_polls: int
    count_dialed: int
    count_rejected: int
    call_result: str  # WP, ANSWERED, ABANDONED, TIMEOUT
    from_displayname: str


@dataclass
class AuditLog:
    """Audit log entry from audit_log table."""
    id: int
    time_stamp: datetime
    source: int
    ip: str
    action: int
    object_type: int
    user_name: str
    object_name: str
    prev_data: dict  # JSONB
    new_data: dict  # JSONB


@dataclass
class QualityMetrics:
    """Call quality metrics from cl_quality table."""
    call_history_id: str  # UUID
    call_id: int
    time_stamp: datetime
    summary: str
    a_caller: str
    b_caller: str
    a_number: str
    b_number: str
    a_name: str
    b_name: str
    a_codec: str
    b_codec: str
    a_mos_to_pbx: Optional[float]
    b_mos_to_pbx: Optional[float]
    a_mos_from_pbx: Optional[float]
    b_mos_from_pbx: Optional[float]
    a_rtt: Optional[int]
    b_rtt: Optional[int]
    a_rx_loss: Optional[int]
    b_rx_loss: Optional[int]


# DN Type codes
DN_TYPE_MAP = {
    0: "extension",
    1: "external_line",
    2: "ring_group",
    5: "voicemail",
    13: "inbound_routing",
}

# CDR creation methods
CDR_CREATION_METHOD_MAP = {
    "call_init": "Initial call creation",
    "divert": "Diverted/forwarded",
    "transfer": "Transferred",
    "route_to": "Routed to destination",
    "polling": "Polling for available agents",
}

# CDR termination reasons
CDR_TERMINATION_REASON_MAP = {
    "dst_participant_terminated": "Destination ended call",
    "src_participant_terminated": "Source ended call",
    "continued_in": "Call continued elsewhere",
    "cancelled": "Call was cancelled",
    "redirected": "Call was redirected",
    "polling": "Timed out during polling",
    "no_route": "No route available",
    "completed_elsewhere": "Answered elsewhere",
}

# Audit source codes
AUDIT_SOURCE_MAP = {
    0: "Unknown/Internal",
    1: "Web Client",
    18: "MyPhone (mobile app)",
}

# Audit action codes
AUDIT_ACTION_MAP = {
    1: "Create",
    7: "Update",
    17: "Update (different object type)",
    21: "Delete",
    23: "Login",
    25: "Special action",
    52: "System setting",
}

# Audit object type codes
AUDIT_OBJECT_TYPE_MAP = {
    7: "Extension",
    17: "Queue/Ring Group",
    25: "IVR / Digital Receptionist",
    1001: "Web Client (login)",
}