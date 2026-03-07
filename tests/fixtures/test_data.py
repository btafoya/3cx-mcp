"""
Test data fixtures from 3CX backup CSV files.

This module provides parsed test data from the backup folder for use in tests.
"""
import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


def load_backup_csv(backup_dir: Path, table_name: str) -> list[dict[str, Any]]:
    """
    Load data from a backup CSV file.

    Args:
        backup_dir: Path to the backup directory
        table_name: Name of the CSV file (without .csv extension)

    Returns:
        List of dictionaries representing rows
    """
    csv_file = backup_dir / "DbTables" / f"{table_name}.csv"
    if not csv_file.exists():
        return []

    data = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(dict(row))
    return data


def parse_bool(value: str) -> bool:
    """Parse boolean from database representation."""
    if isinstance(value, bool):
        return value
    return value.lower() in ("t", "true", "1", "yes")


def parse_datetime(value: str) -> datetime | None:
    """Parse datetime from database representation."""
    if not value:
        return None
    try:
        # Handle PostgreSQL timestamp format
        if "+" in value:
            value = value.split("+")[0]
        return datetime.fromisoformat(value)
    except (ValueError, AttributeError):
        return None


class CallDataFactory:
    """Factory for creating test call data."""

    @staticmethod
    def from_backup(backup_dir: Path, limit: int | None = None) -> list[dict[str, Any]]:
        """Load call data from backup."""
        rows = load_backup_csv(backup_dir, "cl_calls")

        data = []
        for row in rows[:limit] if limit else rows:
            data.append({
                "id": int(row.get("id", 0)),
                "start_time": parse_datetime(row.get("start_time")),
                "end_time": parse_datetime(row.get("end_time")),
                "is_answered": row.get("is_answered") == "t",
                "ringing_dur": row.get("ringing_dur"),
                "talking_dur": row.get("talking_dur"),
                "q_wait_dur": row.get("q_wait_dur"),
                "call_history_id": row.get("call_history_id"),
                "duplicated": parse_bool(row.get("duplicated", "f")),
                "migrated": parse_bool(row.get("migrated", "f")),
            })

        return data


class QueueCallDataFactory:
    """Factory for creating test queue call data."""

    @staticmethod
    def from_backup(backup_dir: Path, limit: int | None = None) -> list[dict[str, Any]]:
        """Load queue call data from backup."""
        rows = load_backup_csv(backup_dir, "callcent_queuecalls")

        data = []
        for row in rows[:limit] if limit else rows:
            data.append({
                "idcallcent_queuecalls": int(row.get("idcallcent_queuecalls", 0)),
                "q_num": row.get("q_num"),
                "time_start": parse_datetime(row.get("time_start")),
                "time_end": parse_datetime(row.get("time_end")),
                "ts_waiting": row.get("ts_waiting"),
                "ts_polling": row.get("ts_polling"),
                "ts_servicing": row.get("ts_servicing"),
                "ts_locating": row.get("ts_locating"),
                "count_polls": int(row.get("count_polls", 0)),
                "count_dialed": int(row.get("count_dialed", 0)),
                "count_rejected": int(row.get("count_rejected", 0)),
                "count_dials_timed": int(row.get("count_dials_timed", 0)),
                "reason_noanswercode": int(row.get("reason_noanswercode", 0)),
                "reason_failcode": int(row.get("reason_failcode", 0)),
                "reason_noanswerdesc": row.get("reason_noanswerdesc"),
                "reason_faildesc": row.get("reason_faildesc"),
                "call_history_id": row.get("call_history_id"),
                "q_cal": int(row.get("q_cal", 0)),
                "from_userpart": row.get("from_userpart"),
                "from_displayname": row.get("from_displayname"),
                "to_dialednum": row.get("to_dialednum"),
                "to_dn": row.get("to_dn"),
                "to_dntype": int(row.get("to_dntype", 0)),
                "cb_num": row.get("cb_num"),
                "call_result": row.get("call_result"),
                "deal_status": int(row.get("deal_status", 0)),
                "is_visible": parse_bool(row.get("is_visible", "t")),
                "is_agent": parse_bool(row.get("is_agent", "f")),
                "cdr_participant_id": row.get("cdr_participant_id"),
            })

        return data


class AuditLogDataFactory:
    """Factory for creating test audit log data."""

    @staticmethod
    def from_backup(backup_dir: Path, limit: int | None = None) -> list[dict[str, Any]]:
        """Load audit log data from backup."""
        import json

        rows = load_backup_csv(backup_dir, "audit_log")

        data = []
        for row in rows[:limit] if limit else rows:
            # Parse JSON fields
            prev_data = None
            new_data = None
            try:
                if row.get("prev_data"):
                    prev_data = json.loads(row["prev_data"])
                if row.get("new_data"):
                    new_data = json.loads(row["new_data"])
            except json.JSONDecodeError:
                pass

            data.append({
                "id": int(row.get("id", 0)),
                "time_stamp": parse_datetime(row.get("time_stamp")),
                "source": int(row.get("source", 0)),
                "ip": row.get("ip"),
                "action": int(row.get("action", 0)),
                "object_type": int(row.get("object_type", 0)),
                "user_name": row.get("user_name"),
                "object_name": row.get("object_name"),
                "prev_data": prev_data,
                "new_data": new_data,
            })

        return data


class VoicemailDataFactory:
    """Factory for creating test voicemail data."""

    @staticmethod
    def from_backup(backup_dir: Path, limit: int | None = None) -> list[dict[str, Any]]:
        """Load voicemail data from backup."""
        rows = load_backup_csv(backup_dir, "s_voicemail")

        data = []
        for row in rows[:limit] if limit else rows:
            data.append({
                "idcallcent_queuecalls": int(row.get("idcallcent_queuecalls", 0)),
                "wav_file": row.get("wav_file"),
                "callee": row.get("callee"),
                "caller": row.get("caller"),
                "caller_name": row.get("caller_name"),
                "duration": int(row.get("duration", 0)),
                "created_time": row.get("created_time"),
                "heard": parse_bool(row.get("heard", "f")),
                "transcription": row.get("transcription"),
                "sentiment_score": int(row.get("sentiment_score", 0)) if row.get("sentiment_score") else None,
            })

        return data


class MockDataGenerator:
    """Generator for mock test data when backup is unavailable."""

    @staticmethod
    def create_call_record(call_id: int, answered: bool = True) -> dict[str, Any]:
        """Create a mock call record."""
        start = datetime(2026, 3, 7, 10, 0, call_id)
        end = datetime(2026, 3, 7, 10, 0, call_id + 30) if answered else datetime(2026, 3, 7, 10, 0, call_id + 5)

        return {
            "id": call_id,
            "start_time": start,
            "end_time": end,
            "is_answered": "t" if answered else "f",
            "ringing_dur": "00:00:05.000000",
            "talking_dur": "00:00:25.000000" if answered else None,
            "q_wait_dur": "00:00:00.000000",
            "call_history_id": f"call-{call_id}",
            "duplicated": False,
            "migrated": False,
        }

    @staticmethod
    def create_participant(part_id: int, dn: str, dn_type: int = 0) -> dict[str, Any]:
        """Create a mock participant record."""
        return {
            "id": part_id,
            "dn_type": dn_type,
            "dn": dn,
            "caller_number": f"+1555{dn:04d}0000",
            "display_name": f"User {dn}",
            "dn_class": 1,
            "firstlastname": f"User {dn}",
            "did_number": "8005551234",
            "crm_contact": None,
        }

    @staticmethod
    def create_segment(seg_id: int, call_id: int, src_id: int, dst_id: int) -> dict[str, Any]:
        """Create a mock call segment."""
        return {
            "id": seg_id,
            "call_id": call_id,
            "seq_order": 1,
            "seq_group": 1,
            "src_part_id": src_id,
            "dst_part_id": dst_id,
            "start_time": datetime(2026, 3, 7, 10, 0, 0),
            "end_time": datetime(2026, 3, 7, 10, 0, 30),
            "type": 1,
            "action_id": 1,
            "action_party_id": src_id,
            "call_history_id": f"call-{call_id}",
        }

    @staticmethod
    def create_queue_call(qc_id: int, q_num: str, result: str = "ANSWERED") -> dict[str, Any]:
        """Create a mock queue call record."""
        return {
            "idcallcent_queuecalls": qc_id,
            "q_num": q_num,
            "time_start": datetime(2026, 3, 7, 10, 0, qc_id),
            "time_end": datetime(2026, 3, 7, 10, 0, qc_id + 30),
            "ts_waiting": "00:00:10",
            "ts_polling": "00:00:05",
            "ts_servicing": "00:00:15",
            "count_polls": 3,
            "count_dialed": 1,
            "count_rejected": 0,
            "count_dials_timed": 0,
            "call_result": result,
        }