# 3CX PostgreSQL Database Schema Documentation

## Overview

This document describes the PostgreSQL database schema for 3CX v20.0.8.1109, based on an actual production backup.

**3CX Edition:** Professional (Linux)
**Database Type:** PostgreSQL
**Backup Date:** March 6, 2026

---

## Database Structure Summary

| Category | Tables | Purpose |
|----------|--------|---------|
| **Call Logs** | `cl_calls`, `cl_participants`, `cl_segments`, `cl_party_info` | Core call record storage |
| **CDR** | `cdroutput`, `cdrrecordings`, `cdrbilling`, `cdrcrmcontact` | Call detail records for reporting |
| **Recordings** | `recordings`, `recording_participant` | Call recording metadata |
| **Voicemail** | `s_voicemail` | Voicemail messages |
| **Call Center** | `callcent_queuecalls`, `callcent_ag_queuestatus`, `callcent_ag_dropped_calls` | Queue statistics and metrics |
| **Audit** | `audit_log` | Configuration change tracking |
| **Chat** | `chat_conversation`, `chat_message`, `chat_participant` | Web chat/messaging |
| **Meetings** | `meetingsession` | Web meeting sessions |
| **Configuration** | Various `s_*` tables | System settings and config |
| **Quality** | `cl_quality` | Call quality metrics |

---

## Key Tables Overview

### Core Call Tables

```
cl_calls          → Call-level summary (times, durations)
cl_participants   → Who participated in each call
cl_segments       → Call flow segments (routing steps)
cl_party_info     → Detailed party info with billing
```

### CDR Tables

```
cdroutput         → Full CDR with source/destination details
cdrrecordings     → Links recordings to CDRs
cdrbilling        → Billing information
```

### Supporting Tables

```
s_voicemail       → Voicemail messages
recordings        → Call recording metadata
audit_log         → All configuration changes
callcent_queuecalls → Queue call metrics
```

---

## Relationship Diagram

```
┌─────────────┐       ┌─────────────────┐
│   cl_calls   │◄──────│   cdroutput     │
│             │       │                 │
│ id, start    │       │ cdr_id          │
│ end, duration│       │ source_participant_id
│ is_answered  │       │ destination_participant_id
└──────┬──────┘       └─────────────────┘
       │
       ├─────────┬──────────────────┐
       │         │                  │
┌──────▼──────┐ ┌──────────────┐ ┌──────────────┐
│cl_segments  │ │cl_participants│ │cl_party_info │
│call_id,     │ │call_id,      │ │call_id,      │
│seq_order    │ │dn, caller    │ │info_id, role │
└─────────────┘ └──────┬───────┘ └──────┬───────┘
                      │                  │
                      └────────┬─────────┘
                               │
                      ┌───────▼────────┐
                      │  cdroutput    │
                      └────────────────┘

┌────────────────┐         ┌──────────────┐
│   recordings   │◄────────│ cdroutput    │
│                │         │ cdr_id       │
│ recording_url  │         └──────────────┘
│ start_time     │
└────────────────┘
```

---

## Table List

| Table | Rows | Description |
|-------|------|-------------|
| `cl_calls` | 50+ | Call summary records |
| `cl_participants` | 30+ | Call participants |
| `cl_segments` | 30+ | Call flow segments |
| `cl_party_info` | 30+ | Detailed party info |
| `cdroutput` | 30+ | Full CDR records |
| `recordings` | 30+ | Call recordings |
| `s_voicemail` | 30+ | Voicemail messages |
| `audit_log` | 10+ | Audit trail |
| `callcent_queuecalls` | 2+ | Queue call metrics |

---

## Important Notes

1. **No Active Calls Table**: There is no separate `active_calls` table - use `cl_calls` where `end_time` is NULL or in the future
2. **UUIDs**: CDR IDs use UUID format (e.g., `00000000-01dc-688a-2607-57e500000c10`)
3. **Times**: All timestamps are UTC with timezone offset (`+00`)
4. **Duration Format**: Durations are stored as INTERVAL type (`HH:MM:SS.mmmmmm`)
5. **Boolean**: Booleans are stored as `t`/`f` (PostgreSQL style)

---

## Key Findings vs Original Design

| Assumption | Actual | Impact |
|------------|--------|--------|
| Table name `Calls` | `cl_calls` | Update queries |
| Column `CallID` | `id` (integer) | Update queries |
| Column `CallerID` | Not a direct column | Use participants join |
| Table `ActiveCalls` | Does not exist | Use WHERE clause on cl_calls |
| Boolean values | `t`/`f` not `true`/`false` | Update WHERE clauses |
| Duration integer | INTERVAL type | Parse as string |

---

## Related Documentation

- [Call Tables](call-tables.md) - Core call record structure
- [CDR Tables](cdr-tables.md) - Call detail records
- [Configuration Tables](config-tables.md) - Settings and metadata
- [Media Tables](media-tables.md) - Recordings and voicemail