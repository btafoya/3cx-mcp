# 3CX Call Flow Debugging Add-On - Requirements Specification

## Overview

Build an MCP (Model Context Protocol) add-on that runs on the 3CX server to enable Claude Code to debug call flow issues for 3CX Professional edition installations without requiring enterprise XAPI licensing.

**Approach:** Hybrid - Database access for CRUD operations + Log file parsing for detailed flow tracing

---

## User Goals

1. Debug call flow issues in 3CX Professional environments
2. Query and analyze call records (historical and active)
3. Understand call routing decisions and paths
4. Modify routing configurations as needed
5. Access this functionality via Claude Code through MCP

---

## Functional Requirements

### Database Access Layer

#### Read Operations

| ID | Requirement | Description |
|----|-------------|-------------|
| DB-001 | List Calls | Query all call records with filtering and pagination |
| DB-002 | Get Call Details | Retrieve full call record by ID including all metadata |
| DB-003 | Get Active Calls | Query currently active/ongoing calls |
| DB-004 | Get Call History | Query historical call records with date range filter |
| DB-005 | List Extensions | Query all configured extensions |
| DB-006 | Get Extension Details | Retrieve full extension configuration by number/ID |
| DB-007 | List Queues | Query all call queues |
| DB-008 | Get Queue Details | Retrieve queue configuration and member list |
| DB-009 | List Trunks | Query all SIP trunk configurations |
| DB-010 | Get Trunk Details | Retrieve trunk configuration and status |
| DB-011 | Get Call Statistics | Aggregate call data (volume, duration, success/failure rates) |
| DB-012 | Search Calls | Full-text search across call records by number, extension, duration, etc. |
| DB-013 | Get Call Flow Metadata | Retrieve routing path and decision points for a call |

#### Write Operations

| ID | Requirement | Description |
|----|-------------|-------------|
| DB-101 | Create Extension | Add a new extension to the system |
| DB-102 | Update Extension | Modify extension configuration |
| DB-103 | Delete Extension | Remove an extension |
| DB-104 | Create Queue | Add a new call queue |
| DB-105 | Update Queue | Modify queue configuration and members |
| DB-106 | Delete Queue | Remove a call queue |
| DB-107 | Update Routing | Modify call routing rules |
| DB-108 | Update Trunk | Modify SIP trunk configuration |
| DB-109 | Add Queue Member | Add extension to queue |
| DB-110 | Remove Queue Member | Remove extension from queue |

### Log Parsing Layer

| ID | Requirement | Description |
|----|-------------|-------------|
| LOG-001 | Tail Real-time Logs | Stream new log entries as they are written |
| LOG-002 | Query Historical Logs | Search log entries by date/time range |
| LOG-003 | Filter by Call ID | Retrieve all log entries for a specific call |
| LOG-004 | Filter by Extension | Retrieve log entries for a specific extension |
| LOG-005 | Parse SIP Messages | Extract and format SIP protocol messages |
| LOG-006 | Identify Routing Decisions | Parse and highlight routing decisions in logs |
| LOG-007 | Identify Errors | Extract error messages and warnings from logs |
| LOG-008 | Correlate with Database | Link log entries to call records |

### Hybrid Operations

| ID | Requirement | Description |
|----|-------------|-------------|
| HYB-001 | Full Call Trace | Combine database record + log entries for complete call history |
| HYB-002 | Debug Failed Calls | Identify root cause of failed calls using both data sources |
| HYB-003 | Analyze Call Flow | Visualize complete path from incoming trunk to final destination |

---

## Non-Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| NFR-001 | License Compatibility | Must work on 3CX Professional edition (no XAPI requirement) |
| NFR-002 | Server-Side Execution | Runs directly on 3CX server via SSH access |
| NFR-003 | MCP Compatibility | Exposes functionality as MCP tools for Claude Code |
| NFR-004 | Performance | Database queries should return within 2 seconds |
| NFR-005 | Real-time Latency | Log streaming should have < 1 second latency |
| NFR-006 | Security | Database credentials stored securely, no plaintext passwords |
| NFR-007 | Connection Handling | Automatic reconnection to database on connection loss |
| NFR-008 | Error Handling | Graceful handling of missing log files or database downtime |
| NFR-009 | Idempotency | Write operations should be idempotent where possible |
| NFR-010 | Auditing | All write operations should be logged |

---

## Technical Context

### 3CX Professional Database (Expected Structure)

The 3CX PostgreSQL database is expected to contain the following tables (to be verified):

| Table Name | Purpose | Key Fields |
|------------|---------|------------|
| `Calls` | Call records | CallID, CallerID, CalleeID, StartTime, EndTime, Duration, Status, TrunkID |
| `CallHistory` | Historical call data | CallID, Extension, Direction, Duration, Trunk |
| `Extensions` | Extension configuration | ExtensionNumber, FirstName, LastName, Email, AuthID |
| `Queues` | Queue configuration | QueueID, Name, Strategy, Timeout |
| `QueueMembers` | Queue membership | QueueID, ExtensionNumber, Priority |
| `Trunks` | SIP trunk configuration | TrunkID, Name, Host, Port, Status |
| `ActiveCalls` | Currently active calls | CallID, CallerID, CalleeID, StartTime, Status |
| `CDR` | Call detail records | CallID, Date, Duration, Trunk, Extension, Direction |

### 3CX Log File Locations (Expected)

The following log files are expected on 3CX Linux installations (to be verified):

| File/Path | Purpose | Format |
|-----------|---------|--------|
| `/var/lib/3cxpbx/Bin/3CXPhoneSystem.log` | Main system log | Text, timestamped |
| `/var/lib/3cxpbx/Bin/3CXPhoneSystem-*.log` | Rotated logs | Text |
| `/var/log/3cxpbx/` | Additional log directory | Text |
| `/var/lib/3cxpbx/Instance1/Data/Logs/` | Instance-specific logs | Text |

### Database Connection Details (Expected)

| Setting | Expected Value |
|---------|----------------|
| **Database Type** | PostgreSQL |
| **Host** | localhost or /var/run/postgresql |
| **Port** | 5432 (if using TCP) |
| **Database Name** | 3cxpbx (to be verified) |
| **User** | 3cxpbx (to be verified) |
| **Password** | Stored in config file (to be located) |
| **Connection Method** | Unix socket preferred |

---

## Open Questions

1. What is the exact PostgreSQL database name for 3CX Professional on Linux?
2. What are the database credentials and where are they stored?
3. What is the complete database schema (all tables and columns)?
4. What is the exact format of 3CX log files?
5. Where are the log files exactly located on the 3CX server?
6. What configuration files control call routing and how are they structured?
7. Can changes made directly to the database be safely persisted?
8. Are there any database triggers or stored procedures that need to be considered?
9. What is the frequency of log file rotation?
10. Are there any rate limits or performance considerations for database queries?

---

## User Stories

### Story 1: Call Flow Investigation
> As a system administrator, I want to query the complete flow of a failed call so I can identify where the call routing broke down and fix the issue.

**Acceptance Criteria:**
- Can query call record by ID
- Can retrieve all log entries for that call
- Can see the routing path taken (trunk → queue → extension)
- Can identify any errors or warnings during the call

### Story 2: Active Call Monitoring
> As a support engineer, I want to see all currently active calls in real-time so I can diagnose ongoing issues.

**Acceptance Criteria:**
- Can list all active calls
- Can see caller, callee, duration, and current state
- Can receive real-time updates as calls start/end
- Can identify calls stuck in queues

### Story 3: Queue Performance Analysis
> As a manager, I want to analyze queue performance over a time period so I can optimize staffing and routing rules.

**Acceptance Criteria:**
- Can query call statistics for a specific queue
- Can filter by date range
- Can see average wait time, abandoned calls, answered calls
- Can export results

### Story 4: Extension Management
> As an administrator, I want to add, modify, and remove extensions so I can maintain the phone system configuration.

**Acceptance Criteria:**
- Can create a new extension with required parameters
- Can update extension properties
- Can delete an extension
- Changes are reflected in the 3CX system

### Story 5: Routing Rule Modification
> As an administrator, I want to modify call routing rules so I can direct calls differently based on business needs.

**Acceptance Criteria:**
- Can view current routing rules
- Can add new routing rules
- Can modify existing rules
- Changes take effect without service restart

---

## MCP Tools Specification

### Database Query Tools

```
list_calls(filter, limit, offset)
get_call_details(call_id)
get_active_calls()
get_call_history(start_date, end_date, filter)
list_extensions(filter)
get_extension(extension_number)
list_queues()
get_queue(queue_id)
list_trunks()
get_trunk(trunk_id)
get_call_statistics(start_date, end_date, group_by)
search_calls(query, limit)
```

### Database Write Tools

```
create_extension(params)
update_extension(extension_number, params)
delete_extension(extension_number)
create_queue(params)
update_queue(queue_id, params)
delete_queue(queue_id)
add_queue_member(queue_id, extension_number, priority)
remove_queue_member(queue_id, extension_number)
update_routing_rule(rule_id, params)
update_trunk(trunk_id, params)
```

### Log Parsing Tools

```
tail_logs(follow, lines)
query_logs(start_date, end_date, filter)
get_call_logs(call_id)
get_extension_logs(extension_number, start_date, end_date)
parse_sip_messages(log_entry_id)
get_routing_decisions(call_id)
get_errors(start_date, end_date, severity)
```

### Hybrid Tools

```
trace_call(call_id)
debug_failed_call(call_id)
analyze_call_flow(call_id)
```

---

## Next Steps

1. **Verify database schema** - Connect to 3CX PostgreSQL database and document actual table structure
2. **Locate log files** - Find exact log file locations and formats on the 3CX server
3. **Identify credentials** - Locate database connection credentials
4. **Test read access** - Verify database queries work correctly
5. **Test log parsing** - Verify log files can be parsed and correlated with call records
6. **Design MCP interface** - Define exact tool specifications and data models
7. **Implement database layer** - Build PostgreSQL connection and query logic
8. **Implement log layer** - Build log file parser and streaming functionality
9. **Implement hybrid operations** - Build combined database + log operations
10. **Write write operations** - Implement CRUD operations with safety checks
11. **Testing** - Test on actual 3CX Professional instance