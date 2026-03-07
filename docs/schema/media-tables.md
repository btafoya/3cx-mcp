# Media Tables Schema

## `recordings`

Call recording metadata. Stores information about recorded calls including transcription and AI analysis.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id_recording` | INTEGER | Primary key | 63214, 61677 |
| `cl_participants_id` | INTEGER | Link to cl_participants | (empty) |
| `recording_url` | VARCHAR | Path to recording file | `116/[Rasheed, Dina]_116-7196403939_20260224201047(789).wav` |
| `start_time` | TIMESTAMP | Recording start | `2026-02-24 20:10:47.817332+00` |
| `end_time` | TIMESTAMP | Recording end | `2026-02-24 20:11:29.531003+00` |
| `transcription` | TEXT | Full transcription text | |
| `archived` | BOOLEAN | Is archived | `f` |
| `archived_url` | VARCHAR | Archived file URL | `""` |
| `call_type` | INTEGER | Call type code | 1, 2 |
| `sentiment_score` | INTEGER | AI sentiment score (1-5) | |
| `summary` | TEXT | AI-generated summary | |
| `result` | INTEGER | Result code | 0 |
| `cdr_id` | UUID | Link to cdroutput | `00000000-01dc-a5c9-a819-33a1000015a2` |
| `transcribed` | BOOLEAN | Is transcribed | `t`, `f` |
| `emailed` | BOOLEAN | Was emailed | `f` |
| `queue_dn` | VARCHAR | Queue DN if applicable | `803` |
| `transcription_started_at` | TIMESTAMP | When transcription started | |
| `offload_id` | VARCHAR | Offload identifier | |
| `forced` | BOOLEAN | Was forced recording | `f` |

### Call Types

| Code | Description |
|------|-------------|
| 1 | Inbound |
| 2 | Outbound |

### Recording URL Format

```
{extension}/[{Name}]_{extension}_{caller}_{timestamp}(recording_id).wav
```

Example: `116/[Rasheed, Dina]_116-7196403939_20260224201047(789).wav`

### Example Query: Get Recent Recordings

```sql
SELECT
    id_recording,
    recording_url,
    start_time,
    end_time,
    EXTRACT(EPOCH FROM (end_time - start_time)) as duration_seconds,
    sentiment_score,
    transcribed
FROM recordings
ORDER BY start_time DESC
LIMIT 50;
```

### Example Query: Get Recordings by Extension

```sql
SELECT * FROM recordings
WHERE recording_url LIKE $1 || '/%'
ORDER BY start_time DESC;
```

### Example Query: Get Recordings with Transcription

```sql
SELECT
    id_recording,
    recording_url,
    start_time,
    transcription,
    sentiment_score,
    summary
FROM recordings
WHERE transcribed = 't'
   AND transcription IS NOT NULL
ORDER BY start_time DESC;
```

---

## `recording_participant`

Links recordings to specific participants.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `s_voicemail`

Voicemail message storage.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `idcallcent_queuecalls` | INTEGER | ID reference | |
| `__name` | VARCHAR | Internal name | `104/vmail_3214278289_104_20250913150955` |
| `wav_file` | VARCHAR | WAV filename | `vmail_3214278289_104_20250913150955` |
| `callee` | VARCHAR | Destination extension | `104` |
| `caller` | VARCHAR | Caller number | `3214278289` |
| `caller_name` | VARCHAR | Caller name | `PATERNOSTER DEN:Klee Weekends` |
| `duration` | INTEGER | Duration in seconds | `34600` |
| `created_time` | TIMESTAMP | When voicemail created | `20250913150955.00` |
| `heard_time` | TIMESTAMP | When listened to | `20250908131358.00` |
| `removed_time` | TIMESTAMP | When deleted | |
| `notified_time` | TIMESTAMP | When notification sent | `20250913151030.22` |
| `heard` | BOOLEAN | Has been listened to | `t`, `f` |
| `notification_sent` | BOOLEAN | Was notification sent | `1`, `0` |
| `removed` | BOOLEAN | Has been deleted | |
| `notify_failed` | BOOLEAN | Did notification fail | |
| `attempts` | INTEGER | Notification attempts | |
| `last_attempt_time` | TIMESTAMP | Last notification attempt | |
| `lasterror` | TEXT | Last error | |
| `forwarded_by` | VARCHAR | Forwarded by whom | |
| `forwarded_to` | VARCHAR | Forwarded to whom | |
| `forwarded_time` | TIMESTAMP | When forwarded | |
| `transcription` | TEXT | Transcription text | |
| `crm_contact` | VARCHAR | CRM contact reference | |
| `sentiment_score` | INTEGER | Sentiment score | |
| `summary` | TEXT | AI summary | |
| `result` | INTEGER | Result code | |
| `cdr_participant_id` | UUID | Link to CDR participant | `00000000-01db-edc6-719d-5616000009f4` |
| `crm_contact_id` | VARCHAR | CRM contact ID | |
| `pv_heard_by` | VARCHAR | Private view heard by | |

### Example Query: Get Unheard Voicemails

```sql
SELECT
    __name,
    wav_file,
    caller,
    caller_name,
    callee,
    duration,
    created_time
FROM s_voicemail
WHERE heard = 'f'
ORDER BY created_time DESC;
```

### Example Query: Get Voicemail by Extension

```sql
SELECT * FROM s_voicemail
WHERE callee = $1
ORDER BY created_time DESC;
```

---

## `callcent_queuecalls`

Queue call statistics and metrics.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `idcallcent_queuecalls` | INTEGER | Primary key | 2 |
| `q_num` | VARCHAR | Queue number/DN | `807` |
| `time_start` | TIMESTAMP | Queue entry time | `2024-11-08 14:19:00+00` |
| `time_end` | TIMESTAMP | Queue exit time | `2024-11-08 14:19:01+00` |
| `ts_waiting` | INTERVAL | Time waiting in queue | `00:00:00.543344` |
| `ts_polling` | INTERVAL | Time polling agents | `00:00:01.052358` |
| `ts_servicing` | INTERVAL | Time being serviced | `00:00:00` |
| `ts_locating` | INTERVAL | Time locating agents | `00:00:00` |
| `count_polls` | INTEGER | Number of polls | 1 |
| `count_dialed` | INTEGER | Number dialed | 1 |
| `count_rejected` | INTEGER | Number rejected | 0 |
| `count_dials_timed` | INTEGER | Number of timed dials | 1 |
| `reason_noanswercode` | VARCHAR | No answer code | |
| `reason_failcode` | VARCHAR | Failure code | |
| `reason_noanswerdesc` | VARCHAR | No answer description | `Caller dropped the call` |
| `reason_faildesc` | VARCHAR | Failure description | |
| `call_history_id` | UUID | Call history reference | `8484240c93010000_20` |
| `q_cal` | INTEGER | Queue calculation | `151` |
| `from_userpart` | VARCHAR | From user part | `116` |
| `from_displayname` | VARCHAR | From display name | `Desk 2, Front` |
| `to_dialednum` | VARCHAR | Dialed number | |
| `to_dn` | VARCHAR | Destination DN | |
| `to_dntype` | VARCHAR | Destination DN type | |
| `cb_num` | VARCHAR | Callback number | |
| `call_result` | VARCHAR | Call result | `WP` |
| `deal_status` | VARCHAR | Deal status | `0` |
| `is_visible` | BOOLEAN | Is visible | `t`, `f` |
| `is_agent` | BOOLEAN | Is agent | `f` |
| `cdr_participant_id` | UUID | CDR participant ID | |

### Call Results

| Code | Description |
|------|-------------|
| `WP` | Waiting for pickup |
| `ANSWERED` | Answered |
| `ABANDONED` | Abandoned |
| `TIMEOUT` | Timeout |

### Example Query: Get Queue Statistics

```sql
SELECT
    q_num as queue_number,
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE call_result = 'ANSWERED') as answered,
    COUNT(*) FILTER (WHERE call_result = 'ABANDONED') as abandoned,
    COUNT(*) FILTER (WHERE call_result = 'TIMEOUT') as timeout,
    AVG(EXTRACT(EPOCH FROM ts_waiting)) as avg_wait_seconds
FROM callcent_queuecalls
WHERE time_start >= NOW() - INTERVAL '7 days'
GROUP BY q_num;
```

### Example Query: Get Queue Abandoned Calls

```sql
SELECT
    q_num,
    from_displayname as caller,
    time_start,
    EXTRACT(EPOCH FROM ts_waiting) as wait_seconds,
    reason_noanswerdesc
FROM callcent_queuecalls
WHERE call_result = 'ABANDONED'
ORDER BY time_start DESC;
```

---

## `callcent_ag_queuestatus`

Queue agent status (not fully documented - minimal data in backup).

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `callcent_ag_dropped_calls`

Dropped calls by agents (not fully documented - empty in backup).

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## Media File Locations

Based on backup structure:

| Type | Location |
|------|----------|
| **Recordings** | `/var/lib/3cxpbx/Instance1/Data/Recordings/` |
| **Voicemail** | `/var/lib/3cxpbx/Instance1/Data/Voicemail/` |
| **Voicemail Prompts** | `/var/lib/3cxpbx/Instance1/Data/Ivr/Prompts/` |
| **HTTP Prompts** | `/var/lib/3cxpbx/Instance1/Data/HttpPrompts/` |

### Recording Filename Format

```
{extension}/[{Name}]_{extension}_{caller}_{timestamp}(recording_id).wav
```

### Voicemail Filename Format

```
vmail_{caller}_{extension}_{timestamp}.wav
```

---

## Key Queries

### Get Calls with Recordings

```sql
SELECT
    c.id as call_id,
    c.start_time,
    c.is_answered,
    c.talking_dur,
    r.id_recording,
    r.recording_url,
    r.start_time as recording_start,
    r.end_time as recording_end
FROM cl_calls c
JOIN recordings r ON c.id = r.cl_participants_id
WHERE c.start_time >= NOW() - INTERVAL '7 days'
ORDER BY c.start_time DESC;
```

### Get Voicemail with Transcription

```sql
SELECT
    v.idcallcent_queuecalls,
    v.caller,
    v.caller_name,
    v.callee,
    v.duration,
    v.heard,
    v.transcription,
    v.sentiment_score,
    v.summary,
    v.created_time
FROM s_voicemail v
WHERE v.transcription IS NOT NULL
ORDER BY v.created_time DESC;
```