# Configuration Tables Schema

## `audit_log`

Audit trail of all configuration changes made to the 3CX system.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | INTEGER | Primary key | 229, 262, 275 |
| `time_stamp` | TIMESTAMP | When change was made | `2025-11-13 18:12:16.116357+00` |
| `source` | INTEGER | Source code | 0, 1, 18 |
| `ip` | VARCHAR | Source IP address | `192.168.1.1`, `99.189.138.64` |
| `action` | INTEGER | Action type code | 1, 7, 17, 21, 23, 25 |
| `object_type` | INTEGER | Object type code | 7, 17, 25 |
| `user_name` | VARCHAR | User who made change | `119 Tafoya, Brian` |
| `object_name` | VARCHAR | Name of changed object | `104 Phone 3`, `Test Extended Hours call` |
| `prev_data` | JSONB | Previous value (JSON) | `{"LastName":"Phone 23","DisplayName":"Phone 23"}` |
| `new_data` | JSONB | New value (JSON) | `{"LastName":"Phone 3","DisplayName":"Phone 3"}` |

### Source Codes

| Code | Description |
|------|-------------|
| 0 | Unknown/Internal |
| 1 | Web Client |
| 18 | MyPhone (mobile app) |

### Action Codes

| Code | Description |
|------|-------------|
| 1 | Create |
| 7 | Update |
| 17 | Update (different object type) |
| 21 | Delete |
| 23 | Login |
| 25 | Special action |
| 52 | System setting |

### Object Type Codes

| Code | Description |
|------|-------------|
| 7 | Extension |
| 17 | Queue/Ring Group |
| 25 | IVR / Digital Receptionist |
| 1001 | Web Client (login) |

### Example Query: Get Recent Configuration Changes

```sql
SELECT
    time_stamp,
    user_name,
    action,
    object_name,
    prev_data,
    new_data
FROM audit_log
ORDER BY time_stamp DESC
LIMIT 50;
```

### Example Query: Get Changes by User

```sql
SELECT * FROM audit_log
WHERE user_name = $1
ORDER BY time_stamp DESC;
```

### Example Query: Get Extension Changes

```sql
SELECT
    time_stamp,
    user_name,
    object_name,
    prev_data->>'FirstName' as old_first_name,
    new_data->>'FirstName' as new_first_name,
    prev_data->>'LastName' as old_last_name,
    new_data->>'LastName' as new_last_name
FROM audit_log
WHERE object_type = 7
ORDER BY time_stamp DESC;
```

---

## `s_websitelink`

Website links for live chat integration.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - minimal data in backup) | | |

---

## `s_wmpolling`

Webhook polling configuration.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `s_cors_settings`

CORS (Cross-Origin Resource Sharing) settings.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `s_trunklocation`

Trunk location configuration.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `s_reporterconfig`

Report configuration.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `s_reportrequest`

Report request tracking.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `s_scheduledconf`

Scheduled conference settings.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `s_geolocation`

Geolocation settings.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `s_push`

Push notification settings.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `s_wakeupcalls`

Wake-up call configuration.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `s_sbc`

Session Border Controller settings.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `private.refresh_tokens`

OAuth2 refresh tokens (private table).

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - minimal data in backup) | | |

---

## `private.jwt_signing_keys`

JWT signing keys (private table).

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `scheduled_reports`

Scheduled report definitions.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - minimal data in backup) | | |

---

## Configuration XML

The backup also includes `2120859096Db.xml` which contains:

- System parameters
- Music on hold settings
- Codec priorities
- Feature codes (park, unpark, echo test)
- Recording/voicemail retention policies
- OpenAI integration settings
- Google Cloud Vertex AI settings

### Key Parameters from XML

| Parameter | Example Value | Description |
|-----------|---------------|-------------|
| `MUSICONHOLDFILE` | `/var/lib/3cxpbx/Instance1/Data/Ivr/Prompts/onhold.wav` | MOH file |
| `PARK` | `*0` | Park dial code |
| `UNPARK` | `*1` | Unpark dial code |
| `ECHOTEST` | `*777` | Echo test extension |
| `CBTEST` | `*888` | Callback test extension |
| `FAXOVEREMAILGATEWAY` | `888` | Fax extension |
| `DELETE_RECS_OLDER_THEN` | `30` | Recording retention (days) |
| `DELETE_VM_OLDER_THEN` | `30` | Voicemail retention (days) |
| `MS_LOCAL_CODEC_LIST` | `PCMU PCMA G722 G729 OPUS` | Local codec priority |
| `MS_EXTERNAL_CODEC_LIST` | `G729 G722 PCMU PCMA OPUS` | External codec priority |
| `OPENAI_MODEL` | `gpt-4-turbo` | AI model for transcription |
| `OPENAI_SENTIMENT` | [Sentiment analysis prompt] | Sentiment prompt |
| `GOOGLE_LOCATION` | `us-central1` | Google Cloud region |

---

## Key Queries

### Get Configuration Changes for a Specific Object

```sql
SELECT
    time_stamp,
    user_name,
    action,
    prev_data,
    new_data
FROM audit_log
WHERE object_name LIKE '%' || $1 || '%'
ORDER BY time_stamp DESC;
```

### Get Changes by Date Range

```sql
SELECT
    DATE(time_stamp) as change_date,
    COUNT(*) as change_count
FROM audit_log
WHERE time_stamp >= $1 AND time_stamp <= $2
GROUP BY DATE(time_stamp)
ORDER BY change_date DESC;
```