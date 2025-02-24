import jwt
import os
from fastapi import Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer
from starlette.status import HTTP_401_UNAUTHORIZED
from dotenv import load_dotenv


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
OVERRIDE_KEY = os.getenv("OVERRIDE_KEY")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Hämtar den nuvarande användaren baserat på JWT-token.
    """
    credentials_exception = HTTPException(
        status_code=HTTP_401_UNAUTHORIZED,
        detail="Kunde inte validera dina uppgifter",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id: str = payload.get("sub")
        email: str = payload.get("email")

        if user_id is None or email is None:
            raise credentials_exception

        return {"user_id": user_id, "email": email, "role": payload.get("role", [])}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token har gått ut")
    except jwt.InvalidTokenError:
        raise credentials_exception


def get_current_admin_user(
    user: dict = Depends(get_current_user),
    override_key: str = Header(None, alias="X-Override-Key")
):
    """
    Hämtar den nuvarande användaren och kontrollerar om användaren har admin-behörighet,
    eller om en override-nyckel är angiven för admin-åtkomst.
    """
    if override_key and override_key == OVERRIDE_KEY:
        return {
            "user_id": "override_admin",
            "email": "admin@example.com",
            "role": ["admin"],
        }

    if "admin" not in user["role"]:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Åtkomst nekad")

    return user
