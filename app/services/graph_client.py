import httpx
from app.config import settings

class GraphClient:
    """Utility class to interact with Microsoft Graph API using App-Only Auth."""

    def __init__(self):
        self.client_id = settings.msgraph_client_id
        self.client_secret = settings.msgraph_client_secret
        self.tenant_id = settings.msgraph_tenant_id
        self.user_id = settings.msgraph_user_id
        self.folder_name = settings.onedrive_folder
        self.access_token = None

    async def get_access_token(self) -> str:
        """Fetch OAuth2 Client Credentials token."""
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            self.access_token = response.json().get("access_token")
            return self.access_token

    async def upload_file(self, file_name: str, file_bytes: bytes) -> dict:
        """Upload a file to the specified user's OneDrive."""
        if not self.access_token:
            await self.get_access_token()

        # CRITICAL: Using /users/{user_id}/drive instead of /me/drive for app auth
        url = f"https://graph.microsoft.com/v1.0/users/{self.user_id}/drive/root:/{self.folder_name}/{file_name}:/content"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/octet-stream"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=headers, content=file_bytes)
            response.raise_for_status()
            data = response.json()
            
            return {
                "file_id": data.get("id"),
                "url": data.get("webUrl")
            }
