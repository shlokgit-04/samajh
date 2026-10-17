"""Authentication and authorisation.

- register / login / logout with httpOnly SameSite=Strict cookie sessions
- get_current_user and require_admin dependencies
- profile update, data export, full account deletion
Rate-limited per IP; every auth attempt is recorded in security_log (email +
action + IP only, never passwords).
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from . import config, security, store
from .schemas import LoginRequest, PasswordChange, ProfileUpdate, RegisterRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _public_user(user):
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "role_name": config.ROLE_NAMES.get(user["role"], user["role"]),
        "lang": user["lang"],
        "area": user["area"],
        "phone": user["phone"],
        "created_at": user["created_at"],
        "consented": bool(user.get("consented_at")),
    }


def _set_session_cookie(response, token):
    response.set_cookie(
        key=config.COOKIE_NAME,
        value=token,
        max_age=config.ACCESS_TOKEN_DAYS * 86400,
        httponly=True,
        samesite="strict",
        secure=config.COOKIE_SECURE,
        path="/",
    )


def get_current_user(request: Request):
    """Resolve the signed-in user from the session cookie (or Bearer token)."""
    token = request.cookies.get(config.COOKIE_NAME)
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Please sign in to use this feature.")
    payload = security.decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    user = store.get_user(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="This account no longer exists.")
    return user


def optional_user(request: Request):
    """Same as get_current_user but returns None instead of raising."""
    try:
        return get_current_user(request)
    except HTTPException:
        return None


def require_admin(user=Depends(get_current_user)):
    if user["email"].lower() not in config.ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="This action needs an administrator account.")
    return user


def _guard(request, bucket="auth"):
    ip = security.client_ip(request)
    if not security.rate_limiter.allow(bucket, ip):
        raise HTTPException(status_code=429, detail="Too many attempts. Please wait a few minutes and try again.")
    if not security.check_origin(request):
        raise HTTPException(status_code=403, detail="Request blocked (origin check failed).")
    return ip


@router.post("/register")
async def register(req: RegisterRequest, request: Request, response: Response):
    ip = _guard(request)
    email = req.email.lower().strip()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="That email address does not look right.")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Use a password of at least 8 characters.")
    if req.role not in config.SUPPORTED_ROLES:
        raise HTTPException(status_code=400, detail="Unknown occupation selected.")
    if req.lang not in config.SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail="Unknown language selected.")
    if not req.consent:
        raise HTTPException(status_code=400, detail="Please accept the privacy note to create an account.")
    if store.get_user_by_email(email):
        store.log_security(email, "register_duplicate", ip)
        raise HTTPException(status_code=409, detail="An account with this email already exists. Sign in instead.")

    user_id = store.create_user(
        email=email,
        name=req.name.strip(),
        password_hash=security.hash_password(req.password),
        role=req.role,
        lang=req.lang,
        area=req.area,
        phone=req.phone,
        consented=True,
    )
    store.log_security(email, "register_ok", ip)
    token = security.create_token(user_id, req.role)
    _set_session_cookie(response, token)
    user = store.get_user(user_id)
    return {"user": _public_user(user), "langs": list(config.SUPPORTED_LANGS)}


@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    ip = _guard(request)
    email = req.email.lower().strip()
    user = store.get_user_by_email(email)
    if not user or not security.verify_password(req.password, user["password_hash"]):
        store.log_security(email, "login_failed", ip)
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    store.log_security(email, "login_ok", ip)
    token = security.create_token(user["id"], user["role"])
    _set_session_cookie(response, token)
    return {"user": _public_user(user)}


@router.post("/logout")
async def logout(request: Request, response: Response):
    _guard(request)
    response.delete_cookie(config.COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    data = _public_user(user)
    data["scans"] = store.count_scans(user["id"])
    data["applications"] = len(store.list_applications(user["id"]))
    data["retention_days"] = config.SCAN_RETENTION_DAYS
    data["encrypted"] = True
    return data


@router.patch("/me")
async def update_me(req: ProfileUpdate, request: Request, user=Depends(get_current_user)):
    _guard(request)
    fields = req.model_dump(exclude_none=True)
    if "role" in fields and fields["role"] not in config.SUPPORTED_ROLES:
        raise HTTPException(status_code=400, detail="Unknown occupation selected.")
    if "lang" in fields and fields["lang"] not in config.SUPPORTED_LANGS:
        raise HTTPException(status_code=400, detail="Unknown language selected.")
    store.update_user(user["id"], **fields)
    return _public_user(store.get_user(user["id"]))


@router.post("/password")
async def change_password(req: PasswordChange, request: Request, user=Depends(get_current_user)):
    _guard(request)
    if not security.verify_password(req.current_password, user["password_hash"]):
        store.log_security(user["email"], "password_change_failed", security.client_ip(request))
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Use a new password of at least 8 characters.")
    store.update_user(user["id"], password_hash=security.hash_password(req.new_password))
    store.log_security(user["email"], "password_changed", security.client_ip(request))
    return {"ok": True}


@router.get("/export")
async def export_data(request: Request, user=Depends(get_current_user)):
    """Right of access: everything we hold about the user, as a JSON download."""
    _guard(request)
    data = store.export_user_data(user["id"])
    payload = JSONResponse(content=data)
    payload.headers["Content-Disposition"] = f'attachment; filename="samajh-data-{user["id"]}.json"'
    return payload


@router.delete("/me")
async def delete_account(request: Request, response: Response, user=Depends(get_current_user)):
    """Right to erasure: delete the account and every stored scan immediately."""
    _guard(request)
    store.delete_user(user["id"])
    store.log_security(user["email"], "account_deleted", security.client_ip(request))
    response.delete_cookie(config.COOKIE_NAME, path="/")
    return {"ok": True, "message": "Your account and all stored data have been deleted."}
