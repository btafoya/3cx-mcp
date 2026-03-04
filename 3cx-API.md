# 3CX Configuration REST API (XAPI)

**Internal Name:** XAPI

**Introduced:** 3CX Version 20

**Standards:** Built on OData and OpenAPI specifications

**Documentation:**
- [Overview](https://www.3cx.com/docs/configuration-rest-api/)
- [Endpoint Specifications](https://www.3cx.com/docs/configuration-rest-api-endpoints/)

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

**Notes:**
- Access token expires after 60 minutes
- Re-authentication required upon expiration
- Use `Authorization: Bearer {access_token}` header for subsequent requests

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
4. Check "3CX Configuration API Access" checkbox
5. Specify Department and Role for appropriate access level
6. System Owner/System Admin grants system-wide rights
7. Save the API key (client_secret) - shown only once

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
| GET | `/Groups({id})?$expand=Members` | Get department with members |
| POST | `/Groups` | Create department |
| PATCH | `/Groups({id})` | Update department |
| POST | `/Groups/Pbx.DeleteCompanyById` | Delete department |

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
| POST | `/Users` | Create user |
| PATCH | `/Users({id})` | Update user |
| POST | `/Users/Pbx.BatchDelete` | Delete users in batch |

#### List Users

**Query Parameters:**
- `$top`: Limit results (default 100)
- `$skip`: Skip records (default 0)
- `$orderby`: Sort order (e.g., `Number`)
- `$select`: Fields to return (Id, FirstName, LastName, Number, EmailAddress)
- `$expand`: Expand related entities (e.g., `Groups(Rights())`)

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

---

### Parking (Shared Parking)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/Parkings` | List parking slots |
| GET | `/Parkings/Pbx.GetByNumber(number='{number}')` | Get parking by number |
| POST | `/Parkings` | Create shared parking |
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
| GET | `/WebsiteLinks?$filter=Link eq '{link}'` | Check if URL exists |
| POST | `/WebsiteLinks` | Create live chat URL |
| POST | `/WebsiteLinks/Pbx.ValidateLink` | Validate friendly URL |

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
```

---

## Open Questions

1. Are there additional endpoints not documented (e.g., call queues, ring groups, SIP trunks)?
2. Does the API support refresh tokens or only expires_at?
3. Are there rate limits on API calls?
4. What are all available PromptSet GUIDs?
5. What are all valid TimeZoneId values?
6. Does the API support webhooks for real-time updates?

---

## References

- [3CX Configuration API Overview](https://www.3cx.com/docs/configuration-rest-api/)
- [3CX Configuration API Endpoint Specifications](https://www.3cx.com/docs/configuration-rest-api-endpoints/)
- [3CX Community Forums](https://www.3cx.com/community/)