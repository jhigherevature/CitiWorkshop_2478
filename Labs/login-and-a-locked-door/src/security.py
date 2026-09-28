from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

SECRET_KEY = "lab-only-secret-key-never-use-this-one-in-production"
ALGORITHM = "HS256"
TOKEN_LIFETIME = timedelta(minutes=30)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_access_token(username: str) -> str:
    claims = {"sub": username, "exp": datetime.now(timezone.utc) + TOKEN_LIFETIME}
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return claims["sub"]
