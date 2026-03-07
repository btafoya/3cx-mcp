# CDR Tables Schema

## `cdroutput`

Main Call Detail Record table with full source and destination information.

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `cdr_id` | UUID | Unique CDR identifier | `00000000-01dc-688a-2607-57e500000c10` |
| `call_history_id` | UUID | Call history reference | `00000000-01dc-688a-2607-3bc20000028e` |
| `source_participant_id` | UUID | Source participant UUID | `00000000-01dc-688a-2607-582e00000e9d` |
| `source_entity_type` | VARCHAR | Source entity type | `extension`, `external_line`, `script` |
| `source_dn_number` | VARCHAR | Source DN number | `101`, `10001` |
| `source_dn_type` | VARCHAR | Source DN type | `extension`, `provider` |
| `source_dn_name` | VARCHAR | Source DN name | `Jones, Nathan`, `FHSI` |
| `source_participant_name` | VARCHAR | Source participant name | `Jones, Nathan` |
| `source_participant_phone_number` | VARCHAR | Source phone number | `101`, `4073650906` |
| `source_participant_trunk_did` | VARCHAR | Source trunk DID | `383_2318` |
| `source_participant_is_incoming` | BOOLEAN | Is source incoming | `t`, `f` |
| `source_participant_is_already_connected` | BOOLEAN | Was already connected | `t`, `f` |
| `source_participant_group_name` | VARCHAR | Source group name | `__DEFAULT__` |
| `source_participant_billing_suffix` | VARCHAR | Billing suffix | `""` |
| `destination_participant_id` | UUID | Destination participant UUID | `00000000-01dc-688a-2607-585700000e9e` |
| `destination_entity_type` | VARCHAR | Destination entity type | `extension`, `voicemail`, `ring_group_ring_all` |
| `destination_dn_number` | VARCHAR | Destination DN number | `116`, `125`, `803` |
| `destination_dn_type` | VARCHAR | Destination DN type | `extension`, `ring_group_ring_all` |
| `destination_dn_name` | VARCHAR | Destination DN name | `Rasheed, Dina` |
| `destination_participant_name` | VARCHAR | Destination participant name | `Rasheed, Dina` |
| `destination_participant_phone_number` | VARCHAR | Destination phone number | `116` |
| `destination_participant_trunk_did` | VARCHAR | Destination trunk DID | `383_2318` |
| `destination_participant_is_incoming` | BOOLEAN | Is destination incoming | `t`, `f` |
| `destination_participant_is_already_connected` | BOOLEAN | Was already connected | `t`, `f` |
| `destination_participant_group_name` | VARCHAR | Destination group | `__DEFAULT__` |
| `destination_participant_billing_suffix` | VARCHAR | Billing suffix | `""` |
| `base_cdr_id` | UUID | Base CDR for transfers | |
| `originating_cdr_id` | UUID | Originating CDR | |
| `creation_method` | VARCHAR | How CDR was created | `call_init`, `divert`, `transfer`, `route_to` |
| `creation_forward_reason` | VARCHAR | Forward reason | `none`, `forward_all`, `polling` |
| `termination_reason` | VARCHAR | Why call ended | `dst_participant_terminated`, `continued_in`, `cancelled` |
| `terminated_by_participant_id` | UUID | Who terminated | `00000000-01dc-688a-2607-585700000e9e` |
| `continued_in_cdr_id` | UUID | CDR call continued in | |
| `cdr_started_at` | TIMESTAMP | CDR start time | `2025-12-08 21:32:26.70634+00` |
| `cdr_ended_at` | TIMESTAMP | CDR end time | `2025-12-08 21:33:26.895684+00` |
| `cdr_answered_at` | TIMESTAMP | Answer time | `2025-12-08 21:32:29.322063+00` |
| `termination_reason_details` | VARCHAR | Additional details | |
| `processed` | BOOLEAN | Is CDR processed | `t`, `f` |
| `migrated` | BOOLEAN | Is migrated | `t`, `f` |
| `main_call_history_id` | UUID | Main call history | |
| `source_presentation` | VARCHAR | Source presentation name | `Nathan Jones` |
| `offload_id` | VARCHAR | Offload ID | |

### Entity Types

| Type | Description |
|------|-------------|
| `extension` | Phone extension |
| `external_line` / `provider` | SIP trunk / provider |
| `ring_group_ring_all` | Ring group (ring all strategy) |
| `voicemail` | Voicemail box |
| `inbound_routing` | Inbound routing rule |
| `script` | IVR script |
| `outbound_rule` | Outbound rule |

### Creation Methods

| Method | Description |
|--------|-------------|
| `call_init` | Initial call creation |
| `divert` | Diverted/forwarded |
| `transfer` | Transferred |
| `route_to` | Routed to destination |

### Termination Reasons

| Reason | Description |
|--------|-------------|
| `dst_participant_terminated` | Destination ended the call |
| `src_participant_terminated` | Source ended the call |
| `continued_in` | Call continued elsewhere |
| `cancelled` | Call was cancelled |
| `redirected` | Call was redirected |
| `polling` | Call timed out during polling |
| `no_route` | No route available |

### Example Query: Get CDR by Call ID

```sql
SELECT
    cdr_id,
    source_dn_name,
    source_participant_phone_number,
    destination_dn_name,
    destination_participant_phone_number,
    creation_method,
    termination_reason,
    cdr_started_at,
    cdr_ended_at,
    cdr_answered_at
FROM cdroutput
WHERE call_history_id = $1
ORDER BY cdr_started_at;
```

### Example Query: Get Call Chain (Transfer Path)

```sql
WITH RECURSIVE call_chain AS (
    SELECT
        cdr_id,
        source_dn_name,
        destination_dn_name,
        creation_method,
        base_cdr_id,
        originating_cdr_id,
        0 as level
    FROM cdroutput
    WHERE cdr_id = $1

    UNION ALL

    SELECT
        c.cdr_id,
        c.source_dn_name,
        c.destination_dn_name,
        c.creation_method,
        c.base_cdr_id,
        c.originating_cdr_id,
        cc.level + 1
    FROM cdroutput c
    JOIN call_chain cc ON c.originating_cdr_id = cc.cdr_id
)
SELECT * FROM call_chain ORDER BY level, cdr_started_at;
```

---

## `cdrrecordings`

Links CDRs to call recordings.

| Column | Type | Description |
|--------|------|-------------|
| `cdr_id` | UUID | Reference to cdroutput.cdr_id |
| `recording_id` | INTEGER | Reference to recordings.id_recording |

---

## `cdrbilling`

Billing information for CDRs.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## `cdrcrmcontact`

Links CDRs to CRM contacts.

| Column | Type | Description |
|--------|------|-------------|
| (To be documented - empty in backup) | | |

---

## CDR Example Trace

For a call that goes through multiple stages:

1. **Initial**: `external_line` → `inbound_routing` (creation_method: `call_init`)
2. **IVR**: `inbound_routing` → `script` (creation_method: `divert`)
3. **Queue**: `script` → `ring_group_ring_all` (creation_method: `transfer`)
4. **Extension**: `ring_group_ring_all` → `extension` (creation_method: `route_to`)
5. **End**: `extension` terminates (termination_reason: `dst_participant_terminated`)

```sql
SELECT
    creation_method,
    source_entity_type,
    source_dn_number,
    source_dn_name,
    destination_entity_type,
    destination_dn_number,
    destination_dn_name,
    cdr_started_at,
    cdr_ended_at
FROM cdroutput
WHERE call_history_id = $1
ORDER BY cdr_started_at;
```

---

## Key Queries

### Get Failed Calls with Reason

```sql
SELECT
    co.source_dn_name as caller,
    co.destination_dn_name as callee,
    co.termination_reason,
    co.cdr_started_at,
    co.cdr_ended_at
FROM cdroutput co
WHERE co.termination_reason IN ('cancelled', 'no_route', 'polling')
ORDER BY co.cdr_started_at DESC
LIMIT 100;
```

### Get Queue Calls

```sql
SELECT
    co.source_dn_name as caller,
    co.destination_dn_name as queue,
    co.cdr_started_at,
    co.cdr_ended_at,
    EXTRACT(EPOCH FROM (co.cdr_ended_at - co.cdr_started_at)) as duration_seconds
FROM cdroutput co
WHERE co.destination_entity_type = 'ring_group_ring_all'
   OR co.destination_entity_type = 'queue'
ORDER BY co.cdr_started_at DESC
LIMIT 100;
```

### Get Transferred Calls

```sql
SELECT
    co.call_history_id,
    co.source_dn_name as original_caller,
    co.destination_dn_name as final_destination,
    COUNT(*) as transfer_count
FROM cdroutput co
WHERE co.creation_method IN ('transfer', 'divert')
GROUP BY co.call_history_id, co.source_dn_name, co.destination_dn_name
ORDER BY transfer_count DESC
LIMIT 50;
```