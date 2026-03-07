# Call Tables Schema

## `cl_calls`

Core call summary table. Each row represents one call attempt or call flow.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | INTEGER | Primary key, call ID | 1, 2, 3 |
| `start_time` | TIMESTAMP | When the call started | `2020-08-10 21:12:18+00` |
| `end_time` | TIMESTAMP | When the call ended | `2020-08-10 21:12:36+00` |
| `is_answered` | BOOLEAN | Was call answered? | `t`, `f` |
| `ringing_dur` | INTERVAL | Ringing duration | `00:00:04.642111` |
| `talking_dur` | INTERVAL | Talking duration | `00:00:12.810923` |
| `q_wait_dur` | INTERVAL | Queue wait time | `00:00:05` |
| `call_history_id` | UUID | Link to call history | `NULL` or UUID |
| `duplicated` | BOOLEAN | Is duplicate record | `f` |
| `migrated` | BOOLEAN | Is migrated record | `f` |

### Notes

- `is_answered = 'f'` with non-zero `talking_dur` may indicate voicemail pickup
- `q_wait_dur` is only populated for queue calls
- Active calls have `end_time` in the future or NULL

### Example Query: Get Active Calls

```sql
SELECT * FROM cl_calls
WHERE end_time IS NULL OR end_time > NOW()
ORDER BY start_time DESC;
```

### Example Query: Get Failed Calls

```sql
SELECT * FROM cl_calls
WHERE is_answered = 'f'
ORDER BY start_time DESC;
```

---

## `cl_participants`

Who participated in each call. Links extensions, trunks, and other entities to calls.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | INTEGER | Primary key | 1, 2, 3 |
| `dn_type` | INTEGER | DN type code | 0, 1, 2, 5, 13 |
| `dn` | VARCHAR | DN (Directory Number) | `101`, `10000`, `800` |
| `caller_number` | VARCHAR | Caller's phone number | `Ext.101`, `3213013301` |
| `display_name` | VARCHAR | Display name | `Jones, Nathan`, `RingAll` |
| `dn_class` | INTEGER | DN class | 0 |
| `firstlastname` | VARCHAR | First/last name | `Ryan`, `Cordless` |
| `did_number` | VARCHAR | DID (Direct Inward Dialing) | `000000` |
| `crm_contact` | VARCHAR | CRM contact reference | |

### DN Type Codes

| Code | Description |
|------|-------------|
| 0 | Extension |
| 1 | External Line / Provider |
| 2 | Ring Group / Queue |
| 5 | Voicemail |
| 13 | Inbound Routing |

### Example Query: Get Call Participants

```sql
SELECT p.*, c.start_time
FROM cl_participants p
JOIN cl_calls c ON p.id = c.id
WHERE c.id = 1
ORDER BY p.id;
```

---

## `cl_segments`

Call flow segments. Each segment represents a step in the call routing path.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | INTEGER | Primary key | 1, 2, 3 |
| `call_id` | INTEGER | Reference to cl_calls.id | 1, 2 |
| `seq_order` | INTEGER | Sequence order | 1, 2, 3 |
| `seq_group` | INTEGER | Group for parallel segments | 1 |
| `src_part_id` | INTEGER | Source participant ID | 1, 4 |
| `dst_part_id` | INTEGER | Destination participant ID | 2, 5 |
| `start_time` | TIMESTAMP | Segment start | `2020-08-10 21:12:18+00` |
| `end_time` | TIMESTAMP | Segment end | `2020-08-10 21:12:23+00` |
| `type` | INTEGER | Segment type | 1, 2 |
| `action_id` | INTEGER | Action type | 1, 5, 10 |
| `action_party_id` | INTEGER | Party performing action | 6, 8 |
| `call_history_id` | UUID | Link to call history | |

### Segment Types

| Code | Description |
|------|-------------|
| 1 | Ringing |
| 2 | Connected |

### Action Types

| Code | Description |
|------|-------------|
| 1 | Initial |
| 5 | Forward |
| 9 | Queue |
| 10 | Extension |

### Example Query: Get Call Flow Path

```sql
SELECT
    s.seq_order,
    s.type,
    src.dn as source,
    dst.dn as destination,
    s.start_time,
    s.end_time
FROM cl_segments s
JOIN cl_participants src ON s.src_part_id = src.id
JOIN cl_participants dst ON s.dst_part_id = dst.id
WHERE s.call_id = 1
ORDER BY s.seq_order;
```

---

## `cl_party_info`

Detailed information about each party in a call, including billing and status.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | INTEGER | Primary key | 1, 2, 3 |
| `call_id` | INTEGER | Reference to cl_calls.id | 1, 2 |
| `info_id` | INTEGER | Info ID | 1, 4, 5 |
| `role` | INTEGER | Party role (caller/callee) | 1, 2 |
| `is_inbound` | BOOLEAN | Is inbound call | `t`, `f` |
| `end_status` | INTEGER | Call end status | 1, 2 |
| `forward_reason` | INTEGER | Forward reason code | 0, 1 |
| `failure_reason` | INTEGER | Failure reason code | 1, 3 |
| `start_time` | TIMESTAMP | Party start time | `2020-08-10 21:12:18+00` |
| `answer_time` | TIMESTAMP | Answer time | `2020-08-10 21:12:23+00` |
| `end_time` | TIMESTAMP | Party end time | `2020-08-10 21:12:36+00` |
| `billing_code` | VARCHAR | Billing code | `default` |
| `billing_ratename` | VARCHAR | Rate name | `default` |
| `billing_rate` | INTEGER | Rate per minute | 1 |
| `billing_cost` | DECIMAL | Call cost | 0.21 |
| `billing_duration` | INTERVAL | Billable duration | `00:00:12.815462` |
| `recording_url` | VARCHAR | Recording file path | `""` |
| `billing_group` | VARCHAR | Billing group | `""` |

### End Status Codes

| Code | Description |
|------|-------------|
| 1 | Normal |
| 2 | Forwarded |
| 3 | No answer |

### Example Query: Get Call Statistics

```sql
SELECT
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE is_answered = 't') as answered,
    AVG(EXTRACT(EPOCH FROM talking_dur)) as avg_talk_duration
FROM cl_calls
WHERE start_time >= NOW() - INTERVAL '24 hours';
```

---

## Combined Call Trace Query

To get the complete call flow:

```sql
WITH call_info AS (
    SELECT
        c.id as call_id,
        c.start_time,
        c.end_time,
        c.is_answered,
        c.ringing_dur,
        c.talking_dur,
        c.q_wait_dur
    FROM cl_calls c
    WHERE c.id = $1
),
segments AS (
    SELECT
        s.seq_order,
        src.caller_number as source,
        dst.caller_number as destination,
        s.type as segment_type,
        s.start_time,
        s.end_time
    FROM cl_segments s
    JOIN cl_participants src ON s.src_part_id = src.id
    JOIN cl_participants dst ON s.dst_part_id = dst.id
    WHERE s.call_id = $1
    ORDER BY s.seq_order
)
SELECT * FROM call_info, segments;
```

---

## Key Relationships

```
cl_calls (id) ──┬──> cl_segments (call_id)
                │
                ├──> cl_participants (id via segment)
                │
                └──> cl_party_info (call_id)

cl_segments ──┬──> cl_participants (src_part_id)
              └──> cl_participants (dst_part_id)
```