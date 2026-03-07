# 3CX Database Schema Documentation Index

Complete PostgreSQL schema documentation for 3CX v20.0.8.1109 (Professional Edition).

## Overview

- **3CX Version:** v20.0.8.1109
- **Database Type:** PostgreSQL
- **Edition:** Professional
- **Backup Date:** March 6, 2026

## Quick Reference

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `cl_calls` | Call summary | `id`, `start_time`, `end_time`, `is_answered`, `ringing_dur`, `talking_dur` |
| `cl_participants` | Call participants | `id`, `dn`, `caller_number`, `display_name` |
| `cl_segments` | Call flow segments | `call_id`, `seq_order`, `src_part_id`, `dst_part_id` |
| `cl_party_info` | Party details | `call_id`, `role`, `is_inbound`, `end_status`, `billing_*` |
| `cdroutput` | Full CDR | `cdr_id`, `source_*`, `destination_*`, `creation_method`, `termination_reason` |
| `recordings` | Call recordings | `id_recording`, `recording_url`, `cdr_id`, `sentiment_score` |
| `s_voicemail` | Voicemail | `idcallcent_queuecalls`, `caller`, `callee`, `heard`, `transcription` |
| `audit_log` | Audit trail | `time_stamp`, `user_name`, `action`, `object_name`, `prev_data`, `new_data` |
| `callcent_queuecalls` | Queue stats | `q_num`, `time_start`, `ts_waiting`, `call_result` |
| `cl_quality` | Call quality | `call_id`, `a_mos_*`, `b_mos_*`, `a_codec`, `b_codec` |

## Documents

- [Schema Overview](README.md) - Database structure summary and relationships
- [Call Tables](call-tables.md) - `cl_calls`, `cl_participants`, `cl_segments`, `cl_party_info`
- [CDR Tables](cdr-tables.md) - `cdroutput`, `cdrrecordings`, `cdrbilling`
- [Media Tables](media-tables.md) - `recordings`, `s_voicemail`, `callcent_queuecalls`
- [Config Tables](config-tables.md) - `audit_log`, system configuration
- [Other Tables](other-tables.md) - Quality metrics, chat, meetings, CRM

## Key Discoveries

### Actual Schema vs Original Assumptions

| Original Assumption | Actual Schema | Impact |
|---------------------|---------------|--------|
| Table `Calls` | `cl_calls` | Update all queries |
| Column `CallID` | `id` (integer) | Use integer IDs |
| Column `CallerID` | Not direct column | Join via `cl_participants` |
| Table `ActiveCalls` | Does not exist | Use WHERE clause on `cl_calls` |
| Boolean `true/false` | Boolean `t/f` | PostgreSQL style |
| Duration as integer | INTERVAL type | Parse as `HH:MM:SS.mmmmmm` |
| Call ID format | Integer | Not string/UUID |

### Active Calls Query

```sql
SELECT * FROM cl_calls
WHERE end_time IS NULL OR end_time > NOW()
ORDER BY start_time DESC;
```

### Call Flow Trace Query

```sql
SELECT
    s.seq_order,
    src.caller_number as source,
    dst.caller_number as destination,
    s.type,
    s.start_time,
    s.end_time
FROM cl_segments s
JOIN cl_participants src ON s.src_part_id = src.id
JOIN cl_participants dst ON s.dst_part_id = dst.id
WHERE s.call_id = $1
ORDER BY s.seq_order;
```

### Failed Calls Query

```sql
SELECT * FROM cl_calls
WHERE is_answered = 'f'
ORDER BY start_time DESC;
```

## DN Type Codes

| Code | Type | Description |
|------|------|-------------|
| 0 | Extension | Phone extension |
| 1 | External Line | SIP trunk/provider |
| 2 | Ring Group | Queue/ring group |
| 5 | Voicemail | Voicemail box |
| 13 | Inbound Routing | Inbound routing rule |

## Call Segment Types

| Code | Type | Description |
|------|------|-------------|
| 1 | Ringing | Call is ringing |
| 2 | Connected | Call is connected |

## CDR Creation Methods

| Method | Description |
|--------|-------------|
| `call_init` | Initial call creation |
| `divert` | Diverted/forwarded |
| `transfer` | Transferred |
| `route_to` | Routed to destination |
| `polling` | Polling for available agents |

## CDR Termination Reasons

| Reason | Description |
|--------|-------------|
| `dst_participant_terminated` | Destination ended call |
| `src_participant_terminated` | Source ended call |
| `continued_in` | Call continued elsewhere |
| `cancelled` | Call was cancelled |
| `redirected` | Call was redirected |
| `polling` | Timed out during polling |
| `no_route` | No route available |
| `completed_elsewhere` | Answered elsewhere |

## File Locations

| Type | Path |
|------|------|
| Recordings | `/var/lib/3cxpbx/Instance1/Data/Recordings/` |
| Voicemail | `/var/lib/3cxpbx/Instance1/Data/Voicemail/` |
| Voicemail Prompts | `/var/lib/3cxpbx/Instance1/Data/Ivr/Prompts/` |
| HTTP Prompts | `/var/lib/3cxpbx/Instance1/Data/HttpPrompts/` |
| Main Log | `/var/lib/3cxpbx/Bin/3CXPhoneSystem.log` |
| Rotated Logs | `/var/lib/3cxpbx/Bin/3CXPhoneSystem-*.log` |

## Database Connection

| Setting | Expected Value |
|---------|----------------|
| **Database** | PostgreSQL |
| **Socket Directory** | `/var/run/postgresql` |
| **Database Name** | To be verified (likely `3cxpbx`) |
| **User** | To be verified (likely `3cxpbx`) |
| **Connection Method** | Unix socket preferred |

## Next Steps for Implementation

1. **Verify database credentials** - Locate actual DB name, user, password
2. **Test queries** - Run sample queries on live database
3. **Map extensions** - Create extension to DN mapping from `cl_participants`
4. **Verify log format** - Check actual log file format on server
5. **Test real-time monitoring** - Verify active call query works