from datetime import datetime, timedelta, timezone
import hashlib, hmac, secrets, contextvars
import jwt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from app.core.config import settings
from app.db.mongo import get_database

auth_router = APIRouter()
bearer = HTTPBearer(auto_error=False)
_current_user = contextvars.ContextVar("resume_ai_current_user", default=None)

def current_user():
    user = _current_user.get()
    if not user:
        raise HTTPException(401, "Please log in")
    return user

def current_user_id():
    return current_user()["id"]

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return salt.hex() + "$" + digest.hex()

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False

def make_token(user_id: str) -> str:
    if len(settings.jwt_secret) < 32:
        raise HTTPException(500, "JWT_SECRET must be set to a random value of at least 32 characters")
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": user_id, "exp": exp}, settings.jwt_secret, algorithm="HS256")

async def require_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=["HS256"])
        user_doc = await get_database().users.find_one({"_id": ObjectId(payload.get("sub"))})
        if not user_doc:
            raise ValueError("user missing")
    except Exception:
        raise HTTPException(401, "Session expired or invalid. Please log in again.")
    user = {"id": str(user_doc["_id"]), "name": user_doc["name"], "email": user_doc["email"]}
    _current_user.set(user)
    return user

class RegisterBody(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

@auth_router.post("/auth/register")
async def register(body: RegisterBody):
    if len(settings.jwt_secret) < 32:
        raise HTTPException(500, "Configure JWT_SECRET with a random value of at least 32 characters")
    db = get_database()
    email = body.email.lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "An account with this email already exists")
    doc = {"name": body.name.strip(), "email": email, "password_hash": hash_password(body.password),
           "created_at": datetime.now(timezone.utc)}
    result = await db.users.insert_one(doc)
    user = {"id": str(result.inserted_id), "name": doc["name"], "email": email}
    return {"access_token": make_token(user["id"]), "token_type": "bearer", "user": user}

@auth_router.post("/auth/login")
async def login(body: LoginBody):
    if len(settings.jwt_secret) < 32:
        raise HTTPException(500, "Configure JWT_SECRET with a random value of at least 32 characters")
    email = body.email.lower().strip()
    user_doc = await get_database().users.find_one({"email": email})
    if not user_doc or not verify_password(body.password, user_doc.get("password_hash", "")):
        raise HTTPException(401, "Incorrect email or password")
    user = {"id": str(user_doc["_id"]), "name": user_doc["name"], "email": user_doc["email"]}
    return {"access_token": make_token(user["id"]), "token_type": "bearer", "user": user}

@auth_router.get("/auth/me")
async def me(user=Depends(require_user)):
    return user
