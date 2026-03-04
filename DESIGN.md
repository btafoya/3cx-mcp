# 3CX MCP Client Design Document

## 1. Overview

The 3CX MCP client is a Model Context Protocol server component that exposes 3CX XAPI functionality as MCP tools. LLMs (like Claude Code) invoke these tools to manage 3CX VoIP systems programmatically.

### 1.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LLM (Claude Code)                              │
│                                                                              │
│  "Create a user with extension 1001"                                         │
└────────────────────────────────────┬────────────────────────────────────────┘
                                     │ MCP Protocol (stdio/SSE)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        3CX MCP Client (FastMCP)                              │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         FastMCP Server                                │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    Tool Registry                                │  │ │
│  │  │  • create_user()         • list_users()                          │  │ │
│  │  │  • create_department()   • list_departments()                    │  │ │
│  │  │  • create_parking()      • list_parking()                        │  │ │
│  │  │  • create_link()         • validate_link()                       │  │ │
│  │  │  • get_system_info()                                            │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                        │                                     │
│  ┌─────────────────────────────────────▼───────────────────────────────────┐ │
│  │                         Token Manager (auth.py)                        │ │
│  │  • Acquire OAuth2 token                                              │ │
│  │  • Cache token (60 min expiry)                                        │ │
│  │  • Refresh token on expiry                                           │ │
│  └─────────────────────────────────────┬───────────────────────────────────┘ │
│                                        │                                     │
│  ┌─────────────────────────────────────▼───────────────────────────────────┐ │
│  │                    3CX API Client (client.py)                          │ │
│  │  • Build OData queries                                               │ │
│  │  • Make HTTP requests to XAPI                                         │ │
│  │  • Handle error responses                                             │ │
│  └─────────────────────────────────────┬───────────────────────────────────┘ │
└────────────────────────────────────────┼─────────────────────────────────────┘
                                         │ HTTPS + OAuth2 Bearer
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           3CX XAPI Server                                   │
│                                                                              │
│  /xapi/v1/Users    /xapi/v1/Groups    /xapi/v1/Parkings    /xapi/v1/Defs   │
│  /xapi/v1/WebsiteLinks                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
LLM Request → FastMCP Tool Handler → Token Manager → 3CX Client → 3CX XAPI
                                                            ↓
                                                    JSON Response
                                                            ↓
LLM Response ← FastMCP ← Result Parser ← 3CX Client ← 3CX XAPI
```

---

## 2. Component Specification

### 2.1 Main Module (main.py)

```python
"""
3CX MCP Client - Main Entry Point

Uses FastMCP to expose 3CX XAPI functionality as MCP tools.
"""
from mcp.server.fastmcp import FastMCP
from .tools import (
    system,
    departments,
    users,
    parking,
    links
)
from .client import ThreeCXClient
from .auth import TokenManager

def create_mcp_client() -> FastMCP:
    """Create and configure the FastMCP server."""
    client = ThreeCXClient()
    mcp = FastMCP("3CX", json_response=True)

    # Register tools
    register_tools(mcp, client)

    return mcp
```

---

### 2.2 Auth Module (auth.py)

```python
"""
OAuth2 Token Management

Handles OAuth2 client_credentials flow for 3CX XAPI authentication.
"""
import time
from dataclasses import dataclass
from typing import Optional
import httpx

@dataclass
class AccessToken:
    """OAuth2 access token with expiry tracking."""
    token: str
    expires_at: float  # Unix timestamp

    @property
    def is_expired(self) -> bool:
        """Check if token has expired (with 5 min buffer)."""
        return time.time() >= (self.expires_at - 300)

class TokenManager:
    """Manages OAuth2 token lifecycle for 3CX API."""

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        http_client: httpx.AsyncClient
    ):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.http_client = http_client
        self._cached_token: Optional[AccessToken] = None

    async def get_token(self) -> str:
        """Get valid access token, refreshing if expired."""
        if self._cached_token and not self._cached_token.is_expired:
            return self._cached_token.token

        return await self._acquire_token()

    async def _acquire_token(self) -> str:
        """Acquire new access token from 3CX."""
        # POST to /connect/token
        # Return cached token
        pass
```

---

### 2.3 Client Module (client.py)

```python
"""
3CX XAPI Client Wrapper

Provides typed methods for all 3CX API endpoints.
"""
import httpx
from typing import Any, Optional
from urllib.parse import quote

class ThreeCXClientError(Exception):
    """Base exception for 3CX client errors."""
    pass

class AuthenticationError(ThreeCXClientError):
    """Authentication failed."""
    pass

class APIError(ThreeCXClientError):
    """API returned an error response."""
    def __init__(self, status_code: int, message: str, details: Optional[dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"API Error {status_code}: {message}")

class ODataQueryBuilder:
    """Build OData-style query strings."""

    def __init__(self):
        self._filters: list[str] = []
        self._select: list[str] = []
        self._expand: list[str] = []
        self._orderby: Optional[str] = None
        self._top: Optional[int] = None
        self._skip: Optional[int] = None

    def filter(self, expr: str) -> "ODataQueryBuilder":
        """Add filter expression."""
        self._filters.append(expr)
        return self

    def select(self, *fields: str) -> "ODataQueryBuilder":
        """Select specific fields."""
        self._select.extend(fields)
        return self

    def expand(self, *relations: str) -> "ODataQueryBuilder":
        """Expand related entities."""
        self._expand.extend(relations)
        return self

    def top(self, n: int) -> "ODataQueryBuilder":
        """Limit results."""
        self._top = n
        return self

    def skip(self, n: int) -> "ODataQueryBuilder":
        """Skip n records."""
        self._skip = n
        return self

    def build(self) -> str:
        """Build query string."""
        parts = []
        if self._filters:
            parts.append(f"$filter={' and '.join(self._filters)}")
        if self._select:
            parts.append(f"$select={','.join(self._select)}")
        if self._expand:
            parts.append(f"$expand={','.join(self._expand)}")
        if self._orderby:
            parts.append(f"$orderby={self._orderby}")
        if self._top:
            parts.append(f"$top={self._top}")
        if self._skip:
            parts.append(f"$skip={self._skip}")
        return "?" + "&".join(parts) if parts else ""

class ThreeCXClient:
    """Async client for 3CX XAPI."""

    def __init__(
        self,
        server_url: str,
        client_id: str,
        client_secret: str,
        port: int = 5001,
        verify_ssl: bool = True
    ):
        self.base_url = f"{server_url}:{port}/xapi/v1"
        self.token_url = f"{server_url}:{port}/connect/token"
        self.verify_ssl = verify_ssl

        self._http = httpx.AsyncClient(verify_ssl=verify_ssl)
        self._token_manager = TokenManager(
            base_url=self.base_url,
            client_id=client_id,
            client_secret=client_secret,
            http_client=self._http
        )

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
        query: Optional[str] = None
    ) -> Any:
        """Make authenticated request to 3CX API."""
        token = await self._token_manager.get_token()
        url = f"{self.base_url}{path}"
        if query:
            url += query

        headers = {"Authorization": f"Bearer {token}"}

        response = await self._http.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=data
        )

        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> Any:
        """Handle API response, raising appropriate errors."""
        if response.status_code == 401:
            raise AuthenticationError("Invalid or expired token")
        if response.status_code == 404:
            raise ThreeCXClientError("Resource not found")
        if response.status_code >= 400:
            try:
                error_data = response.json()
                raise APIError(
                    status_code=response.status_code,
                    message=error_data.get("error", {}).get("message", "Unknown error"),
                    details=error_data
                )
            except Exception:
                raise APIError(
                    status_code=response.status_code,
                    message=response.text or "Unknown error"
                )

        if response.status_code == 204:
            return None

        return response.json()

    async def close(self):
        """Close HTTP client."""
        await self._http.aclose()
```

---

### 2.4 Tool Specifications

#### System Tools (tools/system.py)

```python
"""
System information and health check tools.
"""
from mcp.server.fastmcp import FastMCP
from ..client import ThreeCXClient

def register(mcp: FastMCP, client: ThreeCXClient):
    """Register system tools."""

    @mcp.tool()
    async def get_system_info() -> dict:
        """Get 3CX system version information.

        Use this to verify API connectivity and get the 3CX version.
        """
        response = await client._request(
            "GET",
            "/Defs",
            query="$select=Id"
        )
        return {
            "version": response.headers.get("X-3CX-Version", "unknown"),
            "connected": True
        }
```

#### Department Tools (tools/departments.py)

```python
"""
Department (Group) management tools.
"""
from mcp.server.fastmcp import FastMCP
from ..client import ThreeCXClient
from ..types import (
    DepartmentCreate,
    DepartmentUpdate,
    Department,
    DepartmentListResult
)

def register(mcp: FastMCP, client: ThreeCXClient):
    """Register department tools."""

    @mcp.tool()
    async def list_departments(
        top: int = 100,
        skip: int = 0,
        expand_members: bool = False
    ) -> DepartmentListResult:
        """List all departments in the 3CX system.

        Args:
            top: Maximum number of departments to return (default: 100)
            skip: Number of departments to skip for pagination (default: 0)
            expand_members: Include department members in response

        Returns:
            List of departments with their IDs, names, and member counts.
        """
        query = ODataQueryBuilder().top(top).skip(skip)
        if expand_members:
            query.expand("Members")

        response = await client._request("GET", "/Groups", query=query.build())
        return DepartmentListResult.model_validate(response)

    @mcp.tool()
    async def create_department(
        name: str,
        language: str = "EN",
        timezone_id: str = "51",
        number_range_from: str = "320",
        number_range_to: str = "339"
    ) -> Department:
        """Create a new department in 3CX.

        Args:
            name: Department name (must be unique)
            language: Language code (default: "EN")
            timezone_id: Timezone ID (default: "51" for UTC)
            number_range_from: Start of user number range
            number_range_to: End of user number range

        Returns:
            Created department with ID and configuration.
        """
        data = DepartmentCreate(
            Name=name,
            Language=language,
            TimeZoneId=timezone_id,
            Props={
                "UserNumberFrom": number_range_from,
                "UserNumberTo": number_range_to
            }
        )

        response = await client._request("POST", "/Groups", data=data.model_dump())
        return Department.model_validate(response)

    @mcp.tool()
    async def get_department(
        department_id: int,
        include_members: bool = False
    ) -> Department:
        """Get details of a specific department.

        Args:
            department_id: The department ID
            include_members: Include department members in response

        Returns:
            Department details including routing configuration.
        """
        query = ODataQueryBuilder()
        if include_members:
            query.expand("Members")

        response = await client._request(
            "GET",
            f"/Groups({department_id})",
            query=query.build()
        )
        return Department.model_validate(response)

    @mcp.tool()
    async def update_department(
        department_id: int,
        name: str | None = None,
        language: str | None = None,
        office_route_number: str | None = None,
        office_route_to: str | None = None
    ) -> None:
        """Update department settings.

        Args:
            department_id: The department ID
            name: New department name (optional)
            language: New language code (optional)
            office_route_number: Office hours routing target number
            office_route_to: Office hours routing destination (Extension, VoiceMail, etc.)
        """
        data = DepartmentUpdate(Id=department_id)

        if name:
            data.Name = name
        if language:
            data.Language = language
        if office_route_number and office_route_to:
            data.OfficeRoute = {
                "Route": {
                    "Number": office_route_number,
                    "To": office_route_to
                }
            }

        await client._request(
            "PATCH",
            f"/Groups({department_id})",
            data=data.model_dump(exclude_none=True)
        )

    @mcp.tool()
    async def delete_department(department_id: int) -> None:
        """Delete a department by ID.

        Warning: This action cannot be undone.

        Args:
            department_id: The department ID to delete
        """
        await client._request(
            "POST",
            "/Groups/Pbx.DeleteCompanyById",
            data={"id": department_id}
        )

    @mcp.tool()
    async def department_exists(name: str) -> bool:
        """Check if a department with the given name exists.

        Args:
            name: Department name to check

        Returns:
            True if department exists, False otherwise
        """
        query = ODataQueryBuilder().filter(f"Name eq '{name}'")
        response = await client._request("GET", "/Groups", query=query.build())
        return len(response.get("value", [])) > 0

    @mcp.tool()
    async def get_department_members(department_id: int) -> list[dict]:
        """List all members of a department.

        Args:
            department_id: The department ID

        Returns:
            List of members with their numbers, types, and names.
        """
        response = await client._request(
            "GET",
            f"/Groups({department_id})",
            query="$expand=Members"
        )
        return response.get("Members", [])
```

#### User Tools (tools/users.py)

```python
"""
User management tools.
"""
from mcp.server.fastmcp import FastMCP
from ..client import ThreeCXClient
from ..types import UserCreate, UserUpdate, User, UserListResult

def register(mcp: FastMCP, client: ThreeCXClient):
    """Register user tools."""

    @mcp.tool()
    async def list_users(
        top: int = 100,
        skip: int = 0,
        orderby: str = "Number",
        expand_groups: bool = True
    ) -> UserListResult:
        """List all users in the 3CX system.

        Args:
            top: Maximum number of users to return (default: 100)
            skip: Number of users to skip for pagination (default: 0)
            orderby: Sort field (default: "Number")
            expand_groups: Include user group memberships and roles

        Returns:
            List of users with extension numbers, names, and group assignments.
        """
        query = ODataQueryBuilder().top(top).skip(skip).orderby(orderby)
        if expand_groups:
            query.select("Id", "FirstName", "LastName", "Number", "EmailAddress")
            query.expand("Groups(Rights())")

        response = await client._request("GET", "/Users", query=query.build())
        return UserListResult.model_validate(response)

    @mcp.tool()
    async def create_user(
        first_name: str,
        last_name: str,
        number: str,
        email: str,
        password: str,
        language: str = "EN",
        require_2fa: bool = True
    ) -> User:
        """Create a new user in 3CX.

        Args:
            first_name: User's first name
            last_name: User's last name
            number: Extension number (must be unique)
            email: User's email address
            password: User's access password
            language: Language code (default: "EN")
            require_2fa: Require two-factor authentication

        Returns:
            Created user with ID and configuration.
        """
        data = UserCreate(
            FirstName=first_name,
            LastName=last_name,
            Number=number,
            EmailAddress=email,
            AccessPassword=password,
            Language=language,
            Require2FA=require_2fa
        )

        response = await client._request("POST", "/Users", data=data.model_dump())
        return User.model_validate(response)

    @mcp.tool()
    async def get_user(user_id: int) -> User:
        """Get details of a specific user.

        Args:
            user_id: The user ID

        Returns:
            User details with all configuration options.
        """
        response = await client._request("GET", f"/Users({user_id})")
        return User.model_validate(response)

    @mcp.tool()
    async def update_user(
        user_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        number: str | None = None,
        click_to_call_id: str | None = None
    ) -> None:
        """Update user settings.

        Args:
            user_id: The user ID
            first_name: New first name (optional)
            last_name: New last name (optional)
            email: New email address (optional)
            number: New extension number (optional)
            click_to_call_id: User-friendly URL for Click-to-Call (optional)
        """
        data = UserUpdate(Id=user_id)

        if first_name:
            data.FirstName = first_name
        if last_name:
            data.LastName = last_name
        if email:
            data.EmailAddress = email
        if number:
            data.Number = number
        if click_to_call_id:
            data.ClickToCallId = click_to_call_id
            data.WebMeetingFriendlyName = click_to_call_id

        await client._request(
            "PATCH",
            f"/Users({user_id})",
            data=data.model_dump(exclude_none=True)
        )

    @mcp.tool()
    async def delete_users(user_ids: list[int]) -> dict:
        """Delete multiple users by ID.

        Warning: This action cannot be undone.

        Args:
            user_ids: List of user IDs to delete

        Returns:
            Result with any errors encountered during deletion.
        """
        response = await client._request(
            "POST",
            "/Users/Pbx.BatchDelete",
            data={"Ids": user_ids}
        )
        return response

    @mcp.tool()
    async def user_exists(email: str) -> bool:
        """Check if a user with the given email exists.

        Args:
            email: Email address to check

        Returns:
            True if user exists, False otherwise
        """
        query = ODataQueryBuilder() \
            .filter(f"tolower(EmailAddress) eq '{email.lower()}'") \
            .top(1)

        response = await client._request("GET", "/Users", query=query.build())
        return len(response.get("value", [])) > 0

    @mcp.tool()
    async def find_user_by_email(email: str) -> dict | None:
        """Find a user by their email address.

        Args:
            email: Email address to search for

        Returns:
            User details if found, None otherwise
        """
        query = ODataQueryBuilder() \
            .filter(f"tolower(EmailAddress) eq '{email.lower()}'") \
            .top(1) \
            .expand("Groups(Rights())")

        response = await client._request("GET", "/Users", query=query.build())
        users = response.get("value", [])
        return users[0] if users else None
```

#### Parking Tools (tools/parking.py)

```python
"""
Shared parking management tools.
"""
from mcp.server.fastmcp import FastMCP
from ..client import ThreeCXClient

def register(mcp: FastMCP, client: ThreeCXClient):
    """Register parking tools."""

    @mcp.tool()
    async def list_parking() -> list[dict]:
        """List all shared parking slots.

        Returns:
            List of parking slots with numbers and IDs.
        """
        response = await client._request("GET", "/Parkings")
        return response.get("value", [])

    @mcp.tool()
    async def create_parking(group_ids: list[int]) -> dict:
        """Create a new shared parking slot.

        Args:
            group_ids: List of group IDs that can access this parking slot

        Returns:
            Created parking slot with assigned number and ID.
        """
        data = {
            "Id": 0,
            "Groups": [{"GroupId": gid} for gid in group_ids]
        }
        response = await client._request("POST", "/Parkings", data=data)
        return response

    @mcp.tool()
    async def get_parking_by_number(number: str) -> dict | None:
        """Get parking slot details by its number.

        Args:
            number: Parking slot number (e.g., "SP11")

        Returns:
            Parking slot details if found, None otherwise
        """
        try:
            response = await client._request(
                "GET",
                f"/Parkings/Pbx.GetByNumber(number='{number}')"
            )
            return response
        except ThreeCXClientError:
            return None

    @mcp.tool()
    async def delete_parking(parking_id: int) -> None:
        """Delete a shared parking slot.

        Args:
            parking_id: The parking slot ID
        """
        await client._request("DELETE", f"/Parkings({parking_id})")
```

#### Live Chat Link Tools (tools/links.py)

```python
"""
Live chat link (WebsiteLink) management tools.
"""
from mcp.server.fastmcp import FastMCP
from ..client import ThreeCXClient

def register(mcp: FastMCP, client: ThreeCXClient):
    """Register live chat link tools."""

    @mcp.tool()
    async def link_exists(link: str) -> bool:
        """Check if a live chat link with the given name exists.

        Args:
            link: Live chat link name to check

        Returns:
            True if link exists, False otherwise
        """
        query = ODataQueryBuilder().filter(f"Link eq '{link}'")
        response = await client._request("GET", "/WebsiteLinks", query=query.build())
        return len(response.get("value", [])) > 0

    @mcp.tool()
    async def validate_link(friendly_name: str, pair: str) -> dict:
        """Validate that a live chat link name is available.

        Args:
            friendly_name: Desired friendly name (e.g., "test")
            pair: Extension number to pair with (e.g., "100")

        Returns:
            Validation result with status and any errors.
        """
        try:
            await client._request(
                "POST",
                "/WebsiteLinks/Pbx.ValidateLink",
                data={"model": {"FriendlyName": friendly_name, "Pair": pair}}
            )
            return {"valid": True, "error": None}
        except APIError as e:
            return {"valid": False, "error": e.message}

    @mcp.tool()
    async def create_link(
        link: str,
        group_number: str,
        chat_enabled: bool = True,
        calls_enabled: bool = True,
        websites: list[str] | None = None
    ) -> dict:
        """Create a new live chat link for a department.

        Args:
            link: Live chat link name (must be unique)
            group_number: Department/group number to route chats to
            chat_enabled: Enable chat functionality
            calls_enabled: Enable click-to-call functionality
            websites: List of website URLs where this link will be used

        Returns:
            Created live chat link with ID and configuration.
        """
        data = {
            "Link": link,
            "Group": group_number,
            "ChatEnabled": chat_enabled,
            "CallsEnabled": calls_enabled,
            "DefaultRecord": True,
            "DN": {
                "Type": "Group",
                "Number": group_number
            },
            "Advanced": {
                "EnableDirectCall": True,
                "CommunicationOptions": "PhoneAndChat"
            },
            "General": {
                "Authentication": "None",
                "Greeting": "DesktopAndMobile"
            },
            "Styling": {
                "Animation": "NoAnimation",
                "Minimized": True
            }
        }

        if websites:
            data["Website"] = websites

        response = await client._request("POST", "/WebsiteLinks", data=data)
        return response
```

---

### 2.5 Type Definitions (types.py)

```python
"""
Pydantic models for 3CX API requests and responses.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any, List, Literal

class DepartmentCreate(BaseModel):
    """Request to create a department."""
    Name: str
    Language: str = "EN"
    TimeZoneId: str = "51"
    AllowCallService: bool = True
    DisableCustomPrompt: bool = True
    Props: Optional[dict] = None

class DepartmentUpdate(BaseModel):
    """Request to update a department."""
    Id: int
    Name: Optional[str] = None
    Language: Optional[str] = None
    OfficeRoute: Optional[dict] = None
    BreakRoute: Optional[dict] = None
    OutOfOfficeRoute: Optional[dict] = None
    HolidaysRoute: Optional[dict] = None
    Props: Optional[dict] = None

class Department(BaseModel):
    """Department from 3CX API."""
    Id: int
    Name: str
    Number: str
    IsDefault: bool = False
    HasMembers: bool = False
    Language: Optional[str] = None
    TimeZoneId: Optional[str] = None
    AllowCallService: Optional[bool] = None
    AnswerAfter: Optional[int] = None
    Members: Optional[List[dict]] = None

    class Config:
        extra = "allow"

class DepartmentListResult(BaseModel):
    """Paginated list of departments."""
    value: List[Department]
    "@odata.context": Optional[str] = None

class UserCreate(BaseModel):
    """Request to create a user."""
    FirstName: str
    LastName: str
    Number: str
    EmailAddress: str
    AccessPassword: str
    Language: str = "EN"
    Require2FA: bool = True
    SendEmailMissedCalls: bool = True
    VMEmailOptions: str = "Notification"
    Id: int = 0

    @field_validator("Number")
    @classmethod
    def validate_number(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("Number must be numeric")
        return v

class UserUpdate(BaseModel):
    """Request to update a user."""
    Id: int
    FirstName: Optional[str] = None
    LastName: Optional[str] = None
    Number: Optional[str] = None
    EmailAddress: Optional[str] = None
    ClickToCallId: Optional[str] = None
    WebMeetingFriendlyName: Optional[str] = None
    CallUsEnableChat: Optional[bool] = None

class User(BaseModel):
    """User from 3CX API."""
    Id: int
    FirstName: str
    LastName: str
    Number: str
    EmailAddress: Optional[str] = None
    Language: Optional[str] = None
    Enable2FA: Optional[bool] = None
    Require2FA: Optional[bool] = None
    Groups: Optional[List[dict]] = None

    class Config:
        extra = "allow"

class UserListResult(BaseModel):
    """Paginated list of users."""
    value: List[User]
    "@odata.context": Optional[str] = None
```

---

## 3. Error Handling Strategy

### 3.1 Error Hierarchy

```
ThreeCXClientError (base)
├── AuthenticationError    (401)
├── NotFoundError          (404)
├── ValidationError        (400)
└── APIError               (all other 4xx/5xx)
```

### 3.2 Error Response Format

```python
{
    "error": {
        "message": "Number:\nWARNINGS.XAPI.ALREADY_IN_USE",
        "details": [
            {
                "target": "Number",
                "message": "WARNINGS.XAPI.ALREADY_IN_USE"
            }
        ]
    }
}
```

### 3.3 Error Messages for Users

| 3CX Error | User-Facing Message |
|-----------|---------------------|
| `WARNINGS.XAPI.ALREADY_IN_USE` | "This {field} is already in use. Please choose another value." |
| `WARNINGS.XAPI.DUPLICATE` | "A record with this name already exists." |
| `unauthorized` | "Authentication failed. Check your API credentials." |
| 404 | "The requested resource was not found." |

---

## 4. Configuration

### 4.1 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `THREECX_SERVER_URL` | Yes | - | 3CX server URL (e.g., https://pbx.example.com) |
| `THREECX_PORT` | No | 5001 | Port number |
| `THREECX_CLIENT_ID` | Yes | - | Service Principal client ID |
| `THREECX_CLIENT_SECRET` | Yes | - | Service Principal API key |
| `THREECX_VERIFY_SSL` | No | true | Verify SSL certificates |

### 4.2 MCP Server Configuration

```python
mcp = FastMCP(
    "3CX",
    json_response=True,
    log_level="INFO"
)
```

---

## 5. Deployment

### 5.1 Transport Options

1. **stdio** - Default, for local development
2. **SSE** - Server-Sent Events, for production
3. **streamable-http** - For production with more control

### 5.2 Installation

```bash
pip install 3cx-mcp
```

### 5.3 MCP Client Configuration (Claude Desktop)

```json
{
  "mcpServers": {
    "3cx": {
      "command": "uvx",
      "args": ["3cx-mcp"],
      "env": {
        "THREECX_SERVER_URL": "https://pbx.example.com",
        "THREECX_CLIENT_ID": "your-client-id",
        "THREECX_CLIENT_SECRET": "your-secret"
      }
    }
  }
}
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

- Token Manager: Token acquisition, caching, expiry
- OData Query Builder: Query string construction
- Client: Request building, error handling

### 6.2 Integration Tests

- Against mock 3CX server
- Test all tool endpoints
- Verify error handling

### 6.3 Manual Testing Checklist

- [ ] Get system info
- [ ] List departments
- [ ] Create department
- [ ] Create user
- [ ] List users
- [ ] Create parking
- [ ] Create live chat link
- [ ] Token refresh after expiry
- [ ] Error handling for invalid inputs

---

## 7. Open Questions

1. **Call Queues**: Not documented in endpoint specs - need to verify if accessible
2. **SIP Trunks**: Not documented - may not be available via XAPI
3. **Rate Limiting**: Unknown - need to test for throttling behavior
4. **Token Refresh**: Does 3CX support refresh tokens or only re-authentication?
5. **Webhooks**: Does XAPI support webhooks for real-time updates?

---

## 8. Dependencies

```
mcp>=0.9.0
httpx>=0.27.0
pydantic>=2.5.0
python-dotenv>=1.0.0
```

---

## 9. File Structure Summary

```
3cx-mcp/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastMCP server entry point
│   ├── auth.py              # OAuth2 token management
│   ├── client.py            # 3CX XAPI client
│   ├── types.py             # Pydantic models
│   └── tools/
│       ├── __init__.py
│       ├── system.py        # System info tool
│       ├── departments.py   # Department management
│       ├── users.py         # User management
│       ├── parking.py       # Parking management
│       └── links.py         # Live chat links
├── tests/
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_client.py
│   ├── test_query_builder.py
│   └── test_tools/
├── pyproject.toml
├── requirements.txt
├── DESIGN.md                # This file
├── 3cx-API.md               # API reference
├── CLAUDE.md                # Project documentation
└── README.md                # User documentation
```