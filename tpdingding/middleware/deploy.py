from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from settings import DeployMode
from settings import settings
from tpdingding.helper.session import pg_session_maker
from tpdingding.helper.session import sqlite_session_maker
from tpdingding.persistence.debug import HybridRepository
from tpdingding.persistence.postgres import PostgresRepository
from tpdingding.persistence.sqlite import SQLiteRepository


async def __cloud_dispatch___(_, request: Request, call_next: RequestResponseEndpoint) -> Response:
    with sqlite_session_maker() as session:
        try:
            response = await call_next(request)
            session.commit()
            return response
        finally:
            session.close()


async def __local_dispatch__(_, request: Request, call_next: RequestResponseEndpoint) -> Response:
    async with pg_session_maker() as session:
        try:
            response = await call_next(request)
            await session.commit()
            return response
        finally:
            await session.close()


REPO_MAP = {
    DeployMode.CLOUD: SQLiteRepository(sqlite_session_maker),
    DeployMode.LOCAL: PostgresRepository(pg_session_maker),
    DeployMode.DEV_DEBUG: HybridRepository(pg_session_maker),
}

DISPATCH_MAP = {
    DeployMode.CLOUD: __cloud_dispatch___,
    DeployMode.LOCAL: __local_dispatch__,
    DeployMode.DEV_DEBUG: __local_dispatch__,
}

DISPATCH = DISPATCH_MAP[settings.dingding_deploy_mode]
REPO = REPO_MAP[settings.dingding_deploy_mode]
