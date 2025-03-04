import os
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from starlette.status import HTTP_401_UNAUTHORIZED
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/token",
    auto_error=(os.getenv("MODE", "production") != "development")
)



def get_current_user(
    token: str = Depends(oauth2_scheme),
):

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

        return {"user_id": user_id, "email": email, "role": payload.get("role", []), "token": token}

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Token har gått ut")
    except jwt.InvalidTokenError:
        raise credentials_exception

def get_current_admin_user(user: dict = Depends(get_current_user)):
    if "admin" not in user["role"]:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Åtkomst nekad")
    return user
