from starlette.middleware.base import BaseHTTPMiddleware

from tpdingding.middleware.deploy import DISPATCH


class DBSessionMiddleware(BaseHTTPMiddleware):
    dispatch = DISPATCH
