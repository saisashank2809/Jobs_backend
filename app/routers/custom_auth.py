import logging
import json
from typing import Any
import jwt
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
import httpx
from starlette.concurrency import run_in_threadpool

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["Auth"])

# Google OAuth Constants
GOOGLE_CLIENT_ID = getattr(settings, "gotrue_external_google_client_id", None)
GOOGLE_CLIENT_SECRET = getattr(settings, "gotrue_external_google_secret", None)

if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    # Try to fall back to generic env names if gotrue ones are missing
    import os
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID") or GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET") or GOOGLE_CLIENT_SECRET

GOOGLE_REDIRECT_URI = "http://localhost:8001/auth/google/callback"
FRONTEND_URL = getattr(settings, "frontend_url", "http://localhost:5173")


def _get_admin_client():
    from supabase import create_client  # type: ignore
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


def get_redirect_uri(request: Request) -> str:
    """Dynamically determine the redirect URI based on the request host."""
    host = request.headers.get("host", "")
    protocol = request.headers.get("x-forwarded-proto", "http" if "localhost" in host or "127.0.0.1" in host else "https")
    return f"{protocol}://{host}/auth/google/callback"

@router.get("/login")
async def google_login(request: Request, role: str = "seeker"):
    """Redirects the user to the Google OAuth consent screen."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google Client ID is not configured.")
        
    import base64
    import json
    state_payload = {"role": role}
    state_str = base64.urlsafe_b64encode(json.dumps(state_payload).encode()).decode()
    
    redirect_uri = get_redirect_uri(request)
    
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid email profile"
        "&access_type=offline"
        "&prompt=select_account"
        f"&state={state_str}"
    )
    return RedirectResponse(auth_url)


@router.get("/callback")
async def google_callback(code: str, request: Request, state: str = None):
    """
    Handles the callback from Google:
    1. Exchanges the code for an access token.
    2. Fetches user profile from Google.
    3. Upserts user in Supabase via Admin API.
    4. Issues a custom JWT.
    """
    if not code:
        raise HTTPException(status_code=400, detail="No code provided by Google.")

    redirect_uri = get_redirect_uri(request)

    # 1. Exchange code for token
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    
    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=token_data)
        if token_res.status_code != 200:
            logger.error(f"Google token exchange failed: {token_res.text}")
            raise HTTPException(status_code=400, detail="Failed to exchange Google code.")
            
        access_token = token_res.json().get("access_token")
        
        # 2. Fetch user profile
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        user_res = await client.get(userinfo_url, headers=headers)
        
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch Google profile.")
            
        google_user = user_res.json()

    email = google_user.get("email")
    full_name = google_user.get("name")
    avatar_url = google_user.get("picture")
    
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email.")

    supabase_client = _get_admin_client()

    # Extract role from state, default to seeker
    role = "seeker"
    if state:
        import base64
        import json
        try:
            # We add padding if needed
            state_pad = state + "=" * (-len(state) % 4)
            state_payload = json.loads(base64.urlsafe_b64decode(state_pad).decode())
            role = state_payload.get("role", "seeker")
        except Exception as e:
            logger.error(f"Failed to decode state parameter: {e}")

    # 3. Upsert user in Supabase
    # We first try to find the user by email in public.users_jobs
    def _find_user():
        return supabase_client.table("users_jobs").select("id").eq("email", email).maybe_single().execute()
        
    existing_user = await run_in_threadpool(_find_user)
    
    if existing_user and existing_user.data:
        user_id = existing_user.data["id"]
    else:
        # User not found in users_jobs. We insert them directly to bypass broken auth.users trigger.
        import uuid
        user_id = str(uuid.uuid4())
        
        try:
            new_profile = {
                "id": user_id,
                "email": email,
                "full_name": full_name or email.split('@')[0],
                "role": role,
                "avatar_url": avatar_url,
                "skills": [],
                "aspirations": []
            }
            def _insert_user():
                return supabase_client.table("users_jobs").insert(new_profile).execute()
            
            await run_in_threadpool(_insert_user)
        except Exception as e:
            logger.error(f"Failed to insert user into users_jobs: {e}")
            raise HTTPException(status_code=500, detail="Failed to create user profile.")

    # 4. Generate custom JWT token using SUPABASE_JWT_SECRET
    # This allows existing FastAPI endpoints expecting Supabase JWTs to work perfectly.
    now = datetime.now(timezone.utc)
    payload = {
        "aud": "authenticated",
        "exp": (now + timedelta(days=7)).timestamp(),
        "iat": now.timestamp(),
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "app_metadata": {
            "provider": "google",
            "providers": ["google"]
        },
        "user_metadata": {
            "full_name": full_name,
            "avatar_url": avatar_url
        }
    }
    
    # Supabase uses HS256 by default
    jwt_secret = settings.supabase_jwt_secret
    access_token = jwt.encode(payload, jwt_secret, algorithm="HS256")
    
    # Dynamically redirect based on environment
    host = request.headers.get("host", "")
    if "localhost" in host or "127.0.0.1" in host:
        base_url = "http://localhost:5173"
    else:
        base_url = FRONTEND_URL.rstrip("/")
        
    redirect_url = f"{base_url}/auth/callback?access_token={access_token}"
    return RedirectResponse(redirect_url)
