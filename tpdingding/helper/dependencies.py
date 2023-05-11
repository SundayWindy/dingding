import secrets

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.security import HTTPBasic
from fastapi.security import HTTPBasicCredentials

from settings import settings
from tpdingding.model.context import Context

security = HTTPBasic()


def get_context(request: Request) -> Context:
    return request.state.context


def login(credentials: HTTPBasicCredentials = Depends(security)):
    current_username_bytes = credentials.username.encode("utf8")
    is_correct_username = secrets.compare_digest(current_username_bytes, settings.dingding_secret_user.encode('utf8'))
    current_password_bytes = credentials.password.encode("utf8")
    is_correct_password = secrets.compare_digest(
        current_password_bytes, settings.dingding_secret_password.encode('utf8')
    )
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="没有权限",
        )
    return credentials.username
