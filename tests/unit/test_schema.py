"""
Unit tests for database schema definitions.
"""
from datetime import datetime
from decimal import Decimal

import pytest

from src.database.schema import (
    CallStatus,
    CallDirection,
    DnType,
    SegmentType,
    CallRecord,
    Participant,
    Segment,
    PartyInfo,
    CdrOutput,
    Recording,
    Voicemail,
    QueueStats,
    AuditLog,
    QualityMetrics,
    DN_TYPE_MAP,
    CDR_CREATION_METHOD_MAP,
    CDR_TERMINATION_REASON_MAP,
    AUDIT_SOURCE_MAP,
    AUDIT_ACTION_MAP,
    AUDIT_OBJECT_TYPE_MAP,
)


class TestCallStatus:
    """Tests for CallStatus enum."""

    def test_call_status_values(self):
        """Test CallStatus enum values."""
        assert CallStatus.ANSWERED.value == "t"
        assert CallStatus.NOT_ANSWERED.value == "f"


class TestCallDirection:
    """Tests for CallDirection enum."""

    def test_call_direction_values(self):
        """Test CallDirection enum values."""
        assert CallDirection.INBOUND.value == "t"
        assert CallDirection.OUTBOUND.value == "f"


class TestDnType:
    """Tests for DnType enum."""

    def test_dn_type_values(self):
        """Test DnType enum values."""
        assert DnType.EXTENSION.value == "0"
        assert DnType.EXTERNAL_LINE.value == "1"
        assert DnType.RING_GROUP.value == "2"
        assert DnType.VOICEMAIL.value == "5"
        assert DnType.INBOUND_ROUTING.value == "13"


class TestSegmentType:
    """Tests for SegmentType enum."""

    def test_segment_type_values(self):
        """Test SegmentType enum values."""
        assert SegmentType.RINGING.value == "1"
        assert SegmentType.CONNECTED.value == "2"


class TestCallRecord:
    """Tests for CallRecord dataclass."""

    def test_call_record_creation(self):
        """Test CallRecord creation."""
        record = CallRecord(
            id=1,
            start_time=datetime(2026, 3, 7, 10, 0, 0),
            end_time=datetime(2026, 3, 7, 10, 0, 30),
            is_answered=True,
            ringing_dur="00:00:05.000000",
            talking_dur="00:00:25.000000",
            q_wait_dur="00:00:02.000000",
            call_history_id="abc-123-def",
            duplicated=False,
            migrated=False,
        )

        assert record.id == 1
        assert record.is_answered is True
        assert record.duplicated is False
        assert record.migrated is False

    def test_call_record_duration_seconds(self):
        """Test duration_seconds property."""
        record = CallRecord(
            id=1,
            start_time=datetime(2026, 3, 7, 10, 0, 0),
            end_time=datetime(2026, 3, 7, 10, 0, 30),
            is_answered=True,
            ringing_dur="00:00:05.000000",
            talking_dur="00:00:25.500000",
            q_wait_dur="00:00:02.000000",
            call_history_id=None,
            duplicated=False,
            migrated=False,
        )

        assert record.duration_seconds == 25

    def test_call_record_duration_seconds_none(self):
        """Test duration_seconds property with None."""
        record = CallRecord(
            id=1,
            start_time=datetime(2026, 3, 7, 10, 0, 0),
            end_time=datetime(2026, 3, 7, 10, 0, 30),
            is_answered=False,
            ringing_dur="00:00:05.000000",
            talking_dur=None,
            q_wait_dur=None,
            call_history_id=None,
            duplicated=False,
            migrated=False,
        )

        assert record.duration_seconds is None


class TestParticipant:
    """Tests for Participant dataclass."""

    def test_participant_creation(self):
        """Test Participant creation."""
        participant = Participant(
            id=1,
            dn_type=0,
            dn="100",
            caller_number="+15551234567",
            display_name="John Doe",
            dn_class=1,
            firstlastname="Doe John",
            did_number="8005551234",
            crm_contact=None,
        )

        assert participant.id == 1
        assert participant.dn_type == 0
        assert participant.dn == "100"
        assert participant.caller_number == "+15551234567"
        assert participant.display_name == "John Doe"


class TestSegment:
    """Tests for Segment dataclass."""

    def test_segment_creation(self):
        """Test Segment creation."""
        segment = Segment(
            id=1,
            call_id=100,
            seq_order=1,
            seq_group=1,
            src_part_id=10,
            dst_part_id=20,
            start_time=datetime(2026, 3, 7, 10, 0, 0),
            end_time=datetime(2026, 3, 7, 10, 0, 5),
            type=1,
            action_id=1,
            action_party_id=10,
            call_history_id="abc-123",
        )

        assert segment.id == 1
        assert segment.call_id == 100
        assert segment.seq_order == 1
        assert segment.src_part_id == 10
        assert segment.dst_part_id == 20


class TestPartyInfo:
    """Tests for PartyInfo dataclass."""

    def test_party_info_creation(self):
        """Test PartyInfo creation."""
        party = PartyInfo(
            id=1,
            call_id=100,
            info_id=1,
            role=0,
            is_inbound=True,
            end_status=0,
            forward_reason=0,
            failure_reason=0,
            start_time=datetime(2026, 3, 7, 10, 0, 0),
            answer_time=datetime(2026, 3, 7, 10, 0, 2),
            end_time=datetime(2026, 3, 7, 10, 0, 30),
            billing_code=None,
            billing_ratename=None,
            billing_rate=None,
            billing_cost=Decimal("0.50"),
            billing_duration="00:00:30",
            recording_url="https://example.com/recording.wav",
        )

        assert party.id == 1
        assert party.call_id == 100
        assert party.is_inbound is True
        assert party.billing_cost == Decimal("0.50")
        assert party.recording_url == "https://example.com/recording.wav"


class TestCdrOutput:
    """Tests for CdrOutput dataclass."""

    def test_cdr_output_creation(self):
        """Test CdrOutput creation."""
        cdr = CdrOutput(
            cdr_id="abc-123-def",
            call_history_id="xyz-789-uvw",
            source_participant_id="src-123",
            source_entity_type="extension",
            source_dn_number="100",
            source_dn_type="0",
            source_dn_name="John Doe",
            source_participant_name="John Doe",
            source_participant_phone_number="+15551234567",
            source_participant_is_incoming=False,
            destination_participant_id="dst-456",
            destination_entity_type="extension",
            destination_dn_number="200",
            destination_dn_type="0",
            destination_dn_name="Jane Smith",
            destination_participant_name="Jane Smith",
            creation_method="call_init",
            termination_reason="dst_participant_terminated",
            cdr_started_at=datetime(2026, 3, 7, 10, 0, 0),
            cdr_ended_at=datetime(2026, 3, 7, 10, 0, 30),
            cdr_answered_at=datetime(2026, 3, 7, 10, 0, 2),
        )

        assert cdr.cdr_id == "abc-123-def"
        assert cdr.creation_method == "call_init"
        assert cdr.termination_reason == "dst_participant_terminated"


class TestRecording:
    """Tests for Recording dataclass."""

    def test_recording_creation(self):
        """Test Recording creation."""
        recording = Recording(
            id_recording=1,
            cl_participants_id=100,
            recording_url="https://example.com/recording.wav",
            start_time=datetime(2026, 3, 7, 10, 0, 0),
            end_time=datetime(2026, 3, 7, 10, 0, 30),
            transcription="Call about billing",
            call_type=1,
            sentiment_score=4,
            summary="Customer was satisfied",
            cdr_id="abc-123",
            transcribed=True,
            queued_dn="800",
        )

        assert recording.id_recording == 1
        assert recording.recording_url == "https://example.com/recording.wav"
        assert recording.transcription == "Call about billing"
        assert recording.sentiment_score == 4
        assert recording.transcribed is True


class TestVoicemail:
    """Tests for Voicemail dataclass."""

    def test_voicemail_creation(self):
        """Test Voicemail creation."""
        voicemail = Voicemail(
            idcallcent_queuecalls=1,
            wav_file="vmail_123.wav",
            callee="100",
            caller="+15551234567",
            caller_name="John Doe",
            duration=30,
            created_time="1762502400",
            heard=False,
            transcription="Please call me back",
            sentiment_score=3,
        )

        assert voicemail.idcallcent_queuecalls == 1
        assert voicemail.callee == "100"
        assert voicemail.caller == "+15551234567"
        assert voicemail.duration == 30
        assert voicemail.heard is False


class TestQueueStats:
    """Tests for QueueStats dataclass."""

    def test_queue_stats_creation(self):
        """Test QueueStats creation."""
        stats = QueueStats(
            idcallcent_queuecalls=1,
            q_num="800",
            time_start=datetime(2026, 3, 7, 10, 0, 0),
            time_end=datetime(2026, 3, 7, 10, 0, 30),
            ts_waiting="00:00:10",
            ts_polling="00:00:05",
            ts_servicing="00:00:15",
            count_polls=3,
            count_dialed=1,
            count_rejected=0,
            call_result="ANSWERED",
            from_displayname="John Doe",
        )

        assert stats.q_num == "800"
        assert stats.call_result == "ANSWERED"
        assert stats.count_dialed == 1


class TestAuditLog:
    """Tests for AuditLog dataclass."""

    def test_audit_log_creation(self):
        """Test AuditLog creation."""
        audit = AuditLog(
            id=1,
            time_stamp=datetime(2026, 3, 7, 10, 0, 0),
            source=0,
            ip="192.168.1.1",
            action=1,
            object_type=7,
            user_name="admin",
            object_name="100 John Doe",
            prev_data={"name": "Old Name"},
            new_data={"name": "New Name"},
        )

        assert audit.id == 1
        assert audit.source == 0
        assert audit.action == 1
        assert audit.object_type == 7
        assert audit.user_name == "admin"


class TestQualityMetrics:
    """Tests for QualityMetrics dataclass."""

    def test_quality_metrics_creation(self):
        """Test QualityMetrics creation."""
        metrics = QualityMetrics(
            call_history_id="abc-123",
            call_id=1,
            time_stamp=datetime(2026, 3, 7, 10, 0, 0),
            summary="Good quality",
            a_caller="sip:100@domain",
            b_caller="sip:200@domain",
            a_number="100",
            b_number="200",
            a_name="John",
            b_name="Jane",
            a_codec="PCMU",
            b_codec="PCMU",
            a_mos_to_pbx=4.5,
            b_mos_to_pbx=4.3,
            a_mos_from_pbx=None,
            b_mos_from_pbx=None,
            a_rtt=50,
            b_rtt=45,
            a_rx_loss=0,
            b_rx_loss=1,
        )

        assert metrics.call_history_id == "abc-123"
        assert metrics.a_mos_to_pbx == 4.5
        assert metrics.a_rtt == 50


class TestConstantMaps:
    """Tests for constant mapping dictionaries."""

    def test_dn_type_map(self):
        """Test DN_TYPE_MAP."""
        assert DN_TYPE_MAP[0] == "extension"
        assert DN_TYPE_MAP[1] == "external_line"
        assert DN_TYPE_MAP[2] == "ring_group"
        assert DN_TYPE_MAP[5] == "voicemail"
        assert DN_TYPE_MAP[13] == "inbound_routing"

    def test_cdr_creation_method_map(self):
        """Test CDR_CREATION_METHOD_MAP."""
        assert "call_init" in CDR_CREATION_METHOD_MAP
        assert "divert" in CDR_CREATION_METHOD_MAP
        assert "transfer" in CDR_CREATION_METHOD_MAP

    def test_cdr_termination_reason_map(self):
        """Test CDR_TERMINATION_REASON_MAP."""
        assert "dst_participant_terminated" in CDR_TERMINATION_REASON_MAP
        assert "src_participant_terminated" in CDR_TERMINATION_REASON_MAP

    def test_audit_source_map(self):
        """Test AUDIT_SOURCE_MAP."""
        assert AUDIT_SOURCE_MAP[0] == "Unknown/Internal"
        assert AUDIT_SOURCE_MAP[1] == "Web Client"
        assert AUDIT_SOURCE_MAP[18] == "MyPhone (mobile app)"

    def test_audit_action_map(self):
        """Test AUDIT_ACTION_MAP."""
        assert AUDIT_ACTION_MAP[1] == "Create"
        assert AUDIT_ACTION_MAP[7] == "Update"
        assert AUDIT_ACTION_MAP[21] == "Delete"
        assert AUDIT_ACTION_MAP[23] == "Login"

    def test_audit_object_type_map(self):
        """Test AUDIT_OBJECT_TYPE_MAP."""
        assert AUDIT_OBJECT_TYPE_MAP[7] == "Extension"
        assert AUDIT_OBJECT_TYPE_MAP[17] == "Queue/Ring Group"
        assert AUDIT_OBJECT_TYPE_MAP[25] == "IVR / Digital Receptionist"
        assert AUDIT_OBJECT_TYPE_MAP[1001] == "Web Client (login)"