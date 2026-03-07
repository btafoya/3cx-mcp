# Other Tables Schema

## `myphone_callhistory_v14`

MyPhone (mobile app) call history.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - minimal data in backup) | | |

---

## `meetingsession`

Web meeting session tracking.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## Chat Tables

### `chat_conversation`

Chat conversation records.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

### `chat_message`

Individual chat messages.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

### `chat_participant`

Chat participants.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

### `chat_conversation_member`

Conversation membership.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

### `chattemplate`

Chat message templates.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

### `chattemplate_language`

Template language variants.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

### `chattemplate_category`

Template categories.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

### `chat_results`

Chat results/tracking.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## Quality Tables

### `cl_quality`

Call quality metrics including MOS scores, jitter, packet loss, codec info.

| Column | Type | Description |
|--------|------|-------------|
| `call_history_id` | UUID | Call history reference |
| `call_id` | INTEGER | Call ID |
| `time_stamp` | TIMESTAMP | When quality measured |
| `summary` | TEXT | Quality summary |
| `transcoding` | | Transcoding info |
| `a_caller` | VARCHAR | Side A caller |
| `b_caller` | VARCHAR | Side B caller |
| `a_number` | VARCHAR | Side A number |
| `b_number` | VARCHAR | Side B number |
| `a_name` | VARCHAR | Side A name |
| `b_name` | VARCHAR | Side B name |
| `a_useragent` | VARCHAR | Side A user agent |
| `b_useragent` | VARCHAR | Side B user agent |
| `a_address` | VARCHAR | Side A address |
| `b_address` | VARCHAR | Side B address |
| `a_tun_address` | VARCHAR | Side A tunnel address |
| `b_tun_address` | VARCHAR | Side B tunnel address |
| `a_rtt` | INTEGER | Side A RTT (Round Trip Time) |
| `b_rtt` | INTEGER | Side B RTT |
| `a_codec` | VARCHAR | Side A codec |
| `b_codec` | VARCHAR | Side B codec |
| `a_mos_to_pbx` | DECIMAL | Side A MOS to PBX |
| `b_mos_to_pbx` | DECIMAL | Side B MOS to PBX |
| `a_mos_from_pbx` | DECIMAL | Side A MOS from PBX |
| `b_mos_from_pbx` | DECIMAL | Side B MOS from PBX |
| `a_rx` | INTEGER | Side A RX packets |
| `a_tx` | INTEGER | Side A TX packets |
| `b_rx` | INTEGER | Side B RX packets |
| `b_tx` | INTEGER | Side B TX packets |
| `a_rx_loss` | INTEGER | Side A RX packet loss |
| `a_tx_loss` | INTEGER | Side A TX packet loss |
| `b_rx_loss` | INTEGER | Side B RX packet loss |
| `b_tx_loss` | INTEGER | Side B TX packet loss |
| `a_rx_jitter` | INTEGER | Side A RX jitter |
| `a_tx_jitter` | INTEGER | Side A TX jitter |
| `b_rx_jitter` | INTEGER | Side B RX jitter |
| `b_tx_jitter` | INTEGER | Side B TX jitter |
| `a_tx_bursts` | INTEGER | Side A TX bursts |
| `b_tx_bursts` | INTEGER | Side B TX bursts |
| `a_burst_len` | INTEGER | Side A burst length |
| `b_burst_len` | INTEGER | Side B burst length |
| `a_duration` | INTEGER | Side A duration |
| `b_duration` | INTEGER | Side B duration |
| `a_participant_id` | UUID | Side A participant ID |
| `b_participant_id` | UUID | Side B participant ID |
| `a_location` | VARCHAR | Side A location |
| `b_location` | VARCHAR | Side B location |

### Quality Metrics Explanation

| Metric | Description |
|--------|-------------|
| **MOS** | Mean Opinion Score (1-5 scale, higher is better) |
| **RTT** | Round Trip Time in milliseconds |
| **Jitter** | Packet delay variation |
| **Packet Loss** | Lost packets |
| **Bursts** | Burst loss events |
| **Codec** | Audio codec used (PCMU, PCMA, G722, G729, OPUS) |

### Example Query: Get Call Quality

```sql
SELECT
    call_id,
    a_name as caller,
    b_name as callee,
    a_codec as caller_codec,
    b_codec as callee_codec,
    a_mos_from_pbx as caller_mos,
    b_mos_from_pbx as callee_mos,
    a_rtt as caller_rtt,
    b_rtt as callee_rtt,
    a_rx_loss as caller_loss,
    b_rx_loss as callee_loss
FROM cl_quality
WHERE call_id = $1;
```

### Example Query: Get Poor Quality Calls

```sql
SELECT
    c.id as call_id,
    c.start_time,
    c.is_answered,
    q.a_mos_from_pbx,
    q.b_mos_from_pbx,
    q.a_codec,
    q.b_codec
FROM cl_calls c
LEFT JOIN cl_quality q ON c.id = q.call_id
WHERE (q.a_mos_from_pbx < 3.0 OR q.b_mos_from_pbx < 3.0)
   AND c.start_time >= NOW() - INTERVAL '30 days'
ORDER BY c.start_time DESC;
```

---

## CRM Integration

### `crm_cache`

CRM contact cache for caller ID lookup.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

### `cdrcrmcontact`

Links CDRs to CRM contacts.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## Summary of Tables by Category

| Category | Tables |
|----------|--------|
| **Call Records** | `cl_calls`, `cl_participants`, `cl_segments`, `cl_party_info` |
| **CDR** | `cdroutput`, `cdrrecordings`, `cdrbilling`, `cdrcrmcontact` |
| **Media** | `recordings`, `recording_participant`, `s_voicemail` |
| **Call Center** | `callcent_queuecalls`, `callcent_ag_queuestatus`, `callcent_ag_dropped_calls` |
| **Quality** | `cl_quality` |
| **Audit** | `audit_log` |
| **Chat** | `chat_conversation`, `chat_message`, `chat_participant`, `chat_template*` |
| **Configuration** | `s_websitelink`, `s_wakeupcalls`, `s_sbc`, various `s_*` tables |
| **Mobile** | `myphone_callhistory_v14` |
| **Meetings** | `meetingsession` |
| **Private** | `private.refresh_tokens`, `private.jwt_signing_keys` |
| **Reports** | `s_reporterconfig`, `s_reportrequest`, `scheduled_reports` |