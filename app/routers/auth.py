"""
Auth endpoints — handles signup and login via the Supabase Admin API.
Routes through the backend to bypass Supabase's free-tier rate limits.
"""

import logging
from pydantic import BaseModel, EmailStr, Field  # type: ignore

from fastapi import APIRouter, HTTPException, status  # type: ignore
from starlette.concurrency import run_in_threadpool

from app.config import settings  # type: ignore
from app.utils.security import get_password_hash

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
    dob: str | None = None
    aspirations: list[str] = Field(default_factory=list, max_length=5)
    avatar_url: str | None = None
    work_preference: str = "Hybrid / Both"
    experience: str = ""
    work_experience_position: str = ""
    work_experience_description: str = ""


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
    return await run_in_threadpool(_signup_internal, req)


def _signup_internal(req: SignUpRequest):
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
                "location": req.location,
                "avatar_url": req.avatar_url
            },
        })

        user = response.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed (no user in response).",
            )

        logger.info(f"User created via admin API: {user.id}")

        # Hash password once for DB storage
        hashed_password = get_password_hash(req.password)

        # Hash password once for DB storage
        hashed_password = get_password_hash(req.password)

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
                "password": hashed_password,
                "full_name": req.full_name,
                "phone": req.phone,
                "location": req.location,
                "skills": req.skills,
                "interests": req.interests,
                "dob": req.dob,
                "aspirations": req.aspirations,
                "avatar_url": req.avatar_url,
                "work_preference": req.work_preference,
                "experience": req.experience,
                "work_experience_position": req.work_experience_position,
                "work_experience_description": req.work_experience_description,
            }).execute()
        else:
            # Update password column for existing row (created by trigger)
            client.table("users_jobs").update({
                "password": hashed_password,
                "role": req.role,
                "full_name": req.full_name,
                "phone": req.phone,
                "location": req.location,
                "skills": req.skills,
                "interests": req.interests,
                "dob": req.dob,
                "aspirations": req.aspirations,
                "avatar_url": req.avatar_url,
                "work_preference": req.work_preference,
                "experience": req.experience,
                "work_experience_position": req.work_experience_position,
                "work_experience_description": req.work_experience_description,
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
    return await run_in_threadpool(_login_internal, req)


def _login_internal(req: SignInRequest):
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
