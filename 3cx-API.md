# 3CX Configuration REST API (XAPI)

**Internal Name:** XAPI

**Introduced:** 3CX Version 20

**Standards:** Built on OData and OpenAPI 3.0.4 specifications

**Documentation:**
- [Overview](https://www.3cx.com/docs/configuration-rest-api/)
- [Endpoint Specifications](https://www.3cx.com/docs/configuration-rest-api-endpoints/)
- [Official Tutorial & Examples](https://github.com/3cx/xapi-tutorial)
- [OpenAPI Spec](https://raw.githubusercontent.com/3cx/xapi-tutorial/master/swagger.yaml)

---

## Authentication

### OAuth2 Client Credentials

The 3CX Configuration API uses OAuth2 with the client_credentials grant.

**Token Endpoint:**
```
POST https://{PBX_FQDN}/connect/token
```

**Request Format:** `application/x-www-form-urlencoded`

| Parameter | Value | Description |
|-----------|-------|-------------|
| `client_id` | Service Principal client ID | DN of the route point (configured when creating API) |
| `client_secret` | Service Principal API key | Shown only once after creation |
| `grant_type` | `client_credentials` | Fixed value |

**Success Response (200):**
```json
{
  "token_type": "Bearer",
  "expires_in": 60,
  "access_token": "ACCESS_TOKEN",
  "refresh_token": null
}
```

**Error Response (401):**
```json
{
  "error": "unauthorized",
  "error_description": "The request requires valid user authentication."
}
```

**Important Notes:**
- Access token expires after 60 minutes
- Only one access token can be created at a time per Service Principal
- Re-authentication required upon expiration
- Use `Authorization: Bearer {access_token}` header for subsequent requests
- Tests run "inband" since only one access token is supported

---

## Configuration

| Environment Variable | Description | Example |
|---------------------|-------------|---------|
| `THREECX_SERVER_URL` | Full URL to 3CX server | `https://pbx.example.com` |
| `THREECX_PORT` | Port number (optional) | `5001` |
| `THREECX_CLIENT_ID` | Service Principal client ID (DN) | `your-client-id` |
| `THREECX_CLIENT_SECRET` | Service Principal API key | `your-secret-here` |

### License Requirement
The Configuration API requires an 8SC and higher ENT/AI or ENT+ license.

### Service Principal Setup

1. Go to 3CX Web Client > Integrations > API
2. Press "Add" to create a new client application
3. Specify the Client ID (DN for accessing the route point)
4. Check "XAPI Access Enabled" (or "3CX Configuration API Access") checkbox
5. Specify Department and Role for appropriate access level
6. System Owner/System Admin grants system-wide rights
7. Save the API key (client_secret) - shown only once

**Warning:** Tests CAN ALTER your PBX. Use a backup or separate instance for testing.

### Token Types
- **Multi-Company Admin Tokens:** Full access to manage all departments and entities
- **User Tokens:** Limited access based on assigned roles and departmental permissions

---

## Base URL

```
https://{PBX_FQDN}/xapi/v1/
```

**Default Ports:**
- HTTPS: 5001
- HTTP: 5000

---

## OData Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `$filter` | Filter results | `$filter=Name eq 'DEFAULT'` |
| `$top` | Limit results (pagination) | `$top=100` |
| `$skip` | Skip records (pagination) | `$skip=0` |
| `$expand` | Expand related entities | `$expand=Groups(Rights())` |
| `$select` | Specify fields to return | `$select=Id,Name,Number` |
| `$orderby` | Sort order | `$orderby=Number` |
| `$search` | Full-text search | `$search='john'` |
| `$count` | Include count in response | `$count=true` |

---

## Available Entity Types

Based on the official swagger.yaml specification, XAPI provides access to the following entities:

| Entity | Description |
|--------|-------------|
| **ActiveCalls** | View and manage ongoing phone calls |
| **ActivityLog** | System event logging |
| **AISettings** | AI resources, vector stores, template management |
| **AntiHackingSettings** | Security configuration |
| **Backups** | System backup and restore |
| **Blocklist** | IP address blocking |
| **BlackListNumbers** | Phone number blacklisting |
| **CallHistoryView** | Call records and reports |
| **CallFlowApps** | Call flow applications |
| **CallFlowScripts** | Call flow script configurations |
| **CallParkingSettings** | Call parking configuration |
| **CallTypesSettings** | Call type definitions |
| **CDRSettings** | Call detail recording settings |
| **ChatHistoryView** | Chat logs |
| **CodecsSettings** | Audio codec configuration |
| **ConferenceSettings** | MCU management, meeting zones |
| **Contacts** | Contact directory management |
| **Countries** | Country information |
| **CountryCodes** | Country code configuration |
| **Defs** | System definitions and version |
| **Groups** | Departments/companies |
| **Parkings** | Shared parking slots |
| **Users** | User accounts |
| **VoicemailSettings** | Voicemail configuration |
| **WebsiteLinks** | Live chat links (Weblink) |

---

## Endpoints

### Authorization

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/connect/token` | Get OAuth2 access token |

---

### System

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/Defs?$select=Id` | Get 3CX version (health check) |
| GET | `/Defs/Codecs` | List available codecs |
| GET | `/Defs/GatewayParameters` | Get gateway parameters |
| GET | `/Defs/Pbx.GetExtensionsProperties()` | Get extension properties |

**Response:**
```json
{
  "@odata.context": "https://PBX_FQDN/xapi/v1/$metadata#Defs(Id)",
  "Id": 0
}
```

**Headers:**
- `X-3CX-Version`: e.g., `20.0.3.6`

---

### Departments (Groups)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/Groups` | List all departments |
| GET | `/Groups?$filter=Name eq '{name}'` | Check if department exists |
| GET | `/Groups({id})` | Get department details |
| GET | `/Groups({id})?$expand=Members` | Get department with members |
| GET | `/Groups({id})/Members` | List department members |
| GET | `/Groups({id})/Rights` | Get department rights |
| POST | `/Groups` | Create department |
| PATCH | `/Groups({id})` | Update department |
| DELETE | `/Groups({id})` | Delete department |
| POST | `/Groups/Pbx.DeleteCompanyById` | Delete department by ID |
| POST | `/Groups/Pbx.DeleteCompanyByNumber` | Delete department by number |
| POST | `/Groups/Pbx.ReplaceGroupLicenseKey` | Replace group license key |
| GET | `/Groups({Id})/Pbx.GetRestrictions()` | Get group restrictions |
| POST | `/Groups/Pbx.LinkGroupPartner` | Link group partner |
| POST | `/Groups/Pbx.UnlinkGroupPartner` | Unlink group partner |

#### Create Department

**Request Body:**
```json
{
  "AllowCallService": true,
  "Id": 0,
  "Language": "EN",
  "Name": "3CX Test",
  "PromptSet": "1e6ed594-af95-4bb4-af56-b957ac87d6d7",
  "Props": {
    "LiveChatMaxCount": 20,
    "PersonalContactsMaxCount": 500,
    "PromptsMaxCount": 10,
    "SystemNumberFrom": "300",
    "SystemNumberTo": "319",
    "TrunkNumberFrom": "340",
    "TrunkNumberTo": "345",
    "UserNumberFrom": "320",
    "UserNumberTo": "339"
  },
  "TimeZoneId": "51",
  "DisableCustomPrompt": true
}
```

**Response (201):**
```json
{
  "@odata.context": "https://PBX_FQDN/xapi/v1/$metadata#Groups/$entity",
  "Name": "3CX Test",
  "Id": 35,
  "Language": "EN",
  "TimeZoneId": "51"
}
```

#### Delete Department

**Request Body:**
```json
{
  "id": 123
}
```

---

### Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/Users` | List users (supports pagination) |
| GET | `/Users?$filter=tolower(EmailAddress) eq '{email}'` | Check if user exists |
| GET | `/Users({id})` | Get user details |
| GET | `/Users({id})/Groups` | Get user group memberships |
| POST | `/Users` | Create user |
| PATCH | `/Users({id})` | Update user |
| DELETE | `/Users({id})` | Delete user |
| POST | `/Users/Pbx.BatchDelete` | Delete users in batch |
| POST | `/Users/Pbx.BulkUpdate` | Bulk update users |
| POST | `/Users/Pbx.MultiUserUpdate` | Multi-user update |
| GET | `/Users/Pbx.GetDuplicatedEmails` | Get duplicated emails |
| GET | `/Users/Pbx.GetFirstAvailableExtensionNumber()` | Get next available extension |
| GET | `/Users/Pbx.GetFirstAvailableHotdeskingNumber()` | Get next available hotdesk |
| POST | `/Users/Pbx.RegeneratePasswords` | Regenerate user passwords |
| POST | `/Users/Pbx.ExportExtensions()` | Export extensions |
| GET | `/Users/Pbx.GetPhoneRegistrars()` | Get phone registrars |
| POST | `/Users/Pbx.RebootPhone` | Reboot user's phone |
| POST | `/Users/Pbx.ReprovisionPhone` | Reprovision user's phone |
| POST | `/Users/Pbx.UpgradePhone` | Upgrade user's phone |
| POST | `/Users/Pbx.InstallFirmware` | Install phone firmware |
| POST | `/Users/Pbx.MakeCall` | Initiate a call |
| POST | `/Users/Pbx.ReprovisionAllPhones` | Reprovision all phones |
| GET | `/Users/Pbx.GetMultiEditGreetings()` | Get multi-edit greetings |
| POST | `/Users/Pbx.MultiDeleteGreeting` | Delete multiple greetings |

#### List Users

**Query Parameters:**
- `$top`: Limit results (default 100)
- `$skip`: Skip records (default 0)
- `$orderby`: Sort order (e.g., `Number`)
- `$select`: Fields to return (Id, FirstName, LastName, Number, EmailAddress)
- `$expand`: Expand related entities (e.g., `Groups(Rights())`)
- `$filter`: Filter results (e.g., `Number eq '100'`)
- `$search`: Full-text search

**Response (200):**
```json
{
  "@odata.context": "https://PBX_FQDN/xapi/v1/$metadata#Users(...)",
  "value": [
    {
      "FirstName": "John",
      "LastName": "Doe",
      "EmailAddress": "john@example.com",
      "Number": "100",
      "Id": 29,
      "Groups": [
        {
          "GroupId": 28,
          "Number": "100",
          "MemberName": "Doe, John",
          "Name": "DEFAULT",
          "Type": "Extension",
          "CanDelete": true,
          "Id": 6,
          "Rights": {
            "RoleName": "system_owners"
          }
        }
      ]
    }
  ]
}
```

#### Create User

**Request Body:**
```json
{
  "AccessPassword": "SecurePassword123!",
  "EmailAddress": "user@example.com",
  "FirstName": "John",
  "Id": 0,
  "Language": "EN",
  "LastName": "Doe",
  "Number": "211",
  "PromptSet": "1e6ed594-af95-4bb4-af56-b957ac87d6d7",
  "SendEmailMissedCalls": true,
  "VMEmailOptions": "Notification",
  "Require2FA": true
}
```

**Response (201):**
```json
{
  "@odata.context": "https://PBX_FQDN/xapi/v1/$metadata#Users/$entity",
  "Enable2FA": false,
  "Require2FA": true,
  "FirstName": "John",
  "LastName": "Doe",
  "EmailAddress": "user@example.com",
  "Number": "211",
  "Id": 38,
  "Language": "EN",
  "SendEmailMissedCalls": true,
  "VMEmailOptions": "Notification",
  "PromptSet": "1e6ed594-af95-4bb4-af56-b957ac87d6d7"
}
```

#### Batch Delete Users

**Request Body:**
```json
{
  "Ids": [37, 38]
}
```

**Response (200):**
```json
{
  "@odata.context": "https://PBX_FQDN/xapi/v1/$metadata#Collection(Pbx.UserDeleteError)",
  "value": []
}
```

#### Get First Available Extension

**Response (200):**
```json
{
  "Number": "102"
}
```

---

### Parking (Shared Parking)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/Parkings` | List parking slots |
| GET | `/Parkings({id})` | Get parking by ID |
| POST | `/Parkings` | Create shared parking |
| PATCH | `/Parkings({id})` | Update parking |
| DELETE | `/Parkings({id})` | Delete parking |

#### Create Shared Parking

**Request Body:**
```json
{
  "Groups": [
    {"GroupId": 122},
    {"GroupId": 95}
  ],
  "Id": 0
}
```

**Response (201):**
```json
{
  "@odata.context": "https://PBX_FQDN/xapi/v1/$metadata#Parkings/$entity",
  "Number": "SP11",
  "Id": 126
}
```

---

### Live Chat Links (WebsiteLinks)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/WebsiteLinks` | List all links |
| GET | `/WebsiteLinks?$filter=Link eq '{link}'` | Check if URL exists |
| GET | `/WebsiteLinks({Link})` | Get link by name |
| POST | `/WebsiteLinks` | Create live chat URL |
| PATCH | `/WebsiteLinks({Link})` | Update link |
| DELETE | `/WebsiteLinks({Link})` | Delete link |
| POST | `/WebsiteLinks/Pbx.ValidateLink` | Validate friendly URL |
| POST | `/WebsiteLinks/Pbx.BulkLinksDelete` | Bulk delete links |

#### Validate Link

**Request Body:**
```json
{
  "model": {
    "FriendlyName": "test",
    "Pair": "100"
  }
}
```

**Response (204):** No content - validation successful

#### Create Live Chat Link

**Request Body:**
```json
{
  "Advanced": {
    "CallTitle": "",
    "CommunicationOptions": "PhoneAndChat",
    "EnableDirectCall": true,
    "IgnoreQueueOwnership": false
  },
  "CallsEnabled": true,
  "ChatEnabled": true,
  "DefaultRecord": true,
  "DN": {
    "Id": 28,
    "Name": "DEFAULT",
    "Number": "GRP0000",
    "Type": "Group"
  },
  "General": {
    "AllowSoundNotifications": true,
    "Authentication": "None",
    "DisableOfflineMessages": false,
    "Greeting": "DesktopAndMobile"
  },
  "Group": "GRP0000",
  "Link": "3cxtest",
  "Name": "",
  "Styling": {
    "Animation": "NoAnimation",
    "Minimized": true
  },
  "Website": ["https://my.website.com"]
}
```

---

### Activity Log

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ActivityLog/Pbx.PurgeLogs` | Purge logs |
| GET | `/ActivityLog/Pbx.GetFilter()` | Get log filter options |
| GET | `/ActivityLog/Pbx.GetLogs(startDate={date},endDate={date},...` | Get filtered logs |

#### Get Logs

**Parameters:**
- `startDate` (required): ISO 8601 datetime
- `endDate` (required): ISO 8601 datetime
- `extension` (optional): Extension number filter
- `call` (optional): Call ID filter
- `severity` (optional): Severity filter

---

### AI Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/AISettings` | Get AI settings |
| PATCH | `/AISettings` | Update AI settings |
| GET | `/AISettings/Pbx.GetAIResources()` | Get available AI resources |
| GET | `/AISettings/Pbx.GetVectorStores(limit={limit},after={after})` | List vector stores |
| GET | `/AISettings/Pbx.GetVectorStore(id={id})` | Get vector store details |
| GET | `/AISettings/Pbx.GetVectorStoreFiles(id={id},...)` | Get vector store files |
| GET | `/AISettings/Pbx.GetAITemplateContents(id={id})` | Get AI template contents |
| POST | `/AISettings/Pbx.CreateVectorStore` | Create vector store |
| POST | `/AISettings/Pbx.UpdateVectorStore` | Update vector store |
| POST | `/AISettings/Pbx.DeleteVectorStore` | Delete vector store |
| POST | `/AISettings/Pbx.DeleteVectorStoreFile` | Delete vector store file |

---

### Backups

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/Backups` | List backups |
| POST | `/Backups` | Create backup |
| DELETE | `/Backups({id})` | Delete backup |
| POST | `/Backups({id})/Pbx.Restore` | Restore backup |
| GET | `/Backups({id})/Pbx.DownloadLink` | Get backup download link |

---

### Active Calls

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ActiveCalls` | List active calls |
| GET | `/ActiveCalls({Id})` | Get specific call |
| POST | `/ActiveCalls({Id})/Pbx.DropCall` | Drop/hang up call |

---

### Contacts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/Contacts` | List contacts |
| POST | `/Contacts` | Create contact |
| PATCH | `/Contacts({id})` | Update contact |
| DELETE | `/Contacts({id})` | Delete contact |
| GET | `/Contacts/Pbx.SearchByNumber(number='{number}')` | Search contact by number |
| POST | `/Contacts/Pbx.BulkDelete` | Bulk delete contacts |

---

### Conference Settings

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ConferenceSettings` | Get conference settings |
| PATCH | `/ConferenceSettings` | Update conference settings |
| POST | `/ConferenceSettings/Pbx.CreateApiKey` | Create MCU API key |
| POST | `/ConferenceSettings/Pbx.DeleteApiKey` | Delete MCU API key |

---

### Blocklist

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/Blocklist` | List blocked IPs |
| POST | `/Blocklist` | Add IP to blocklist |
| DELETE | `/Blocklist({id})` | Remove IP from blocklist |
| POST | `/Blocklist/Pbx.BulkDelete` | Bulk remove IPs |

---

## Role Names (User Permissions)

Valid values for `RoleName`:
- `system_owners`
- `system_admins`
- `group_owners`
- `managers`
- `group_admins`
- `receptionists`
- `users`

---

## Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful update/delete) |
| 400 | Bad Request (validation error, duplicate) |
| 401 | Unauthorized |
| 404 | Not Found |
| 500 | Internal Server Error |

---

## ETag Support

Some endpoints support ETag-based concurrency control. Include the `If-Match` header with the ETag value when updating or deleting resources to prevent conflicts.

---

## Request Examples

### Get OAuth2 Token

```bash
curl -X POST "https://pbx.example.com/connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=YOUR_CLIENT_ID&client_secret=YOUR_SECRET&grant_type=client_credentials"
```

### Get 3CX Version

```bash
curl -X GET "https://pbx.example.com/xapi/v1/Defs?\$select=Id" \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

### List Users

```bash
curl -X GET "https://pbx.example.com/xapi/v1/Users?\$top=100&\$orderby=Number" \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

### Create User

```bash
curl -X POST "https://pbx.example.com/xapi/v1/Users" \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "FirstName": "John",
    "LastName": "Doe",
    "EmailAddress": "john@example.com",
    "Number": "211",
    "AccessPassword": "Secure123!",
    "Id": 0,
    "Language": "EN",
    "Require2FA": true
  }'
```

### Check if Department Exists

```bash
curl -X GET "https://pbx.example.com/xapi/v1/Groups?\$filter=Name eq 'DEFAULT'" \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

### Get First Available Extension Number

```bash
curl -X GET "https://pbx.example.com/xapi/v1/Users/Pbx.GetFirstAvailableExtensionNumber()" \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

### Drop Active Call

```bash
curl -X POST "https://pbx.example.com/xapi/v1/ActiveCalls(123)/Pbx.DropCall" \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

---

## Python Example

```python
import requests

# Get OAuth2 token
token_url = "https://pbx.example.com/connect/token"
token_data = {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_SECRET",
    "grant_type": "client_credentials"
}
token_response = requests.post(token_url, data=token_data)
access_token = token_response.json()["access_token"]

# Make authenticated request
headers = {"Authorization": f"Bearer {access_token}"}

# Get 3CX version
response = requests.get(
    "https://pbx.example.com/xapi/v1/Defs?$select=Id",
    headers=headers
)
print(response.headers.get("X-3CX-Version"))

# List users
response = requests.get(
    "https://pbx.example.com/xapi/v1/Users?$top=10",
    headers=headers
)
print(response.json())

# Get first available extension number
response = requests.get(
    "https://pbx.example.com/xapi/v1/Users/Pbx.GetFirstAvailableExtensionNumber()",
    headers=headers
)
print(response.json())
```

---

## TypeScript Example (from Official Tutorial)

The official 3CX XAPI tutorial provides a TypeScript application with Jest test suites.

**Installation:**
```bash
yarn install
```

**Run tests:**
```bash
yarn jest -i                    # Run all tests
yarn jest -i src/fax.spec.ts   # Run specific test file
```

**Config file (config.ts):**
```typescript
export const config = {
  basePbxUrl: "https://pbx.example.com:5001",
  clientId: "your-client-id",
  clientSecret: "your-secret"
};
```

---

## Open Questions

1. Are there additional endpoints not documented (e.g., call queues, ring groups, SIP trunks)?
2. Does the API support refresh tokens or only re-authentication?
3. Are there rate limits on API calls?
4. What are all available PromptSet GUIDs?
5. What are all valid TimeZoneId values?
6. Does the API support webhooks for real-time updates?

---

## References

- [3CX Configuration API Overview](https://www.3cx.com/docs/configuration-rest-api/)
- [3CX Configuration API Endpoint Specifications](https://www.3cx.com/docs/configuration-rest-api-endpoints/)
- [3CX XAPI Tutorial (GitHub)](https://github.com/3cx/xapi-tutorial)
- [OpenAPI Specification (Swagger)](https://raw.githubusercontent.com/3cx/xapi-tutorial/master/swagger.yaml)
- [3CX Community Forums](https://www.3cx.com/community/)