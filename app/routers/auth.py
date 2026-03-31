"""
Auth endpoints — handles signup and login via the Supabase Admin API.
Routes through the backend to bypass Supabase's free-tier rate limits.
"""

import logging
from pydantic import BaseModel, EmailStr  # type: ignore

from fastapi import APIRouter, HTTPException, status  # type: ignore

from app.config import settings  # type: ignore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "seeker"
    full_name: str | None = None
    phone: str | None = None
    location: str | None = None
    skills: list[str] = []
    interests: str = ""


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    role: str | None = None


# ── Lazy singleton for the admin Supabase client ──────────────
_admin_client = None


def _get_admin_client():
    global _admin_client
    if _admin_client is None:
        from supabase import create_client  # type: ignore
        _admin_client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _admin_client


@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignUpRequest):
    """
    Create a new user via the Supabase Admin API (service role key).
    Bypasses email rate limits completely.
    """
    client = _get_admin_client()

    try:
        # 1. Create user via Admin API — auto-confirms, no email sent
        response = client.auth.admin.create_user({
            "email": req.email,
            "password": req.password,
            "email_confirm": True,
            "user_metadata": {
                "role": req.role,
                "full_name": req.full_name,
                "phone": req.phone,
                "location": req.location
            },
        })

        user = response.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed (no user in response).",
            )

        logger.info(f"User created via admin API: {user.id}")

        # 2. Ensure user exists in public.users table
        existing = (
            client.table("users_jobs")
            .select("id")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        if not existing or not existing.data:
            client.table("users_jobs").insert({
                "id": user.id,
                "email": req.email,
                "role": req.role,
                "password": req.password,
                "full_name": req.full_name,
                "phone": req.phone,
                "location": req.location,
                "skills": req.skills,
                "interests": req.interests,
            }).execute()
        else:
            # Update password column for existing row (created by trigger)
            client.table("users_jobs").update({
                "password": req.password,
                "role": req.role,
                "full_name": req.full_name,
                "phone": req.phone,
                "location": req.location,
                "skills": req.skills,
                "interests": req.interests,
            }).eq("id", user.id).execute()

        # 3. Sign in to get tokens (using the anon-key client approach)
        #    We use the admin client to generate a session link instead
        sign_in_response = client.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })

        session = sign_in_response.session
        if not session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User created but sign-in failed. Try logging in manually.",
            )

        return AuthResponse(**{  # type: ignore
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": user.id,
            "email": req.email,
            "role": req.role,
        })

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "already registered" in error_msg or "already exists" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )
        logger.error(f"Signup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Signup failed: {error_msg}",
        )


@router.post("/login", response_model=AuthResponse)
async def login(req: SignInRequest):
    """
    Login via the backend using the Supabase Admin client.
    Bypasses rate limits on the auth endpoint.
    """
    client = _get_admin_client()

    try:
        response = client.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password,
        })

        session = response.session
        user = response.user

        if not session or not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        # Fetch role from public.users
        profile = (
            client.table("users_jobs")
            .select("role")
            .eq("id", user.id)
            .maybe_single()
            .execute()
        )
        role = profile.data.get("role") if profile and profile.data else None

        return AuthResponse(**{  # type: ignore
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_id": user.id,
            "email": req.email,
            "role": role,
        })

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        if "Invalid login" in error_msg or "invalid" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {error_msg}",
        )
