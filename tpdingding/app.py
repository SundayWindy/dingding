import logging

import httpx
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import JSONResponse

from settings import DeployMode
from settings import settings
from tpdingding.exception import DingDingException
from tpdingding.helper.session import POSTGRES_ENGINE
from tpdingding.helper.session import SQLITE_ENGINE
from tpdingding.middleware.context import ContextMiddleware
from tpdingding.middleware.deploy import REPO
from tpdingding.middleware.session import DBSessionMiddleware
from tpdingding.middleware.track import RequestIdMiddleware
from tpdingding.middleware.track import init_logger
from tpdingding.router import router

init_logger(settings)

app = FastAPI()


app.add_middleware(RequestIdMiddleware)
app.add_middleware(ContextMiddleware)
app.add_middleware(DBSessionMiddleware)
app.include_router(router)


@app.exception_handler(DingDingException)
async def exception_handler(_: Request, exc: DingDingException) -> JSONResponse:
    logging.error(exc.message)
    return JSONResponse(
        content={
            'errcode': exc.errcode,
            'errmsg': exc.message,
        },
        status_code=httpx.codes.INTERNAL_SERVER_ERROR,
    )


@app.on_event('startup')
async def startup():
    if settings.dingding_deploy_mode in (DeployMode.LOCAL, DeployMode.DEV_DEBUG):
        logging.info('部署模式为 %s ，初始化 Postgres 数据库连接', settings.dingding_deploy_mode)
        await POSTGRES_ENGINE.connect()
    elif settings.dingding_deploy_mode == DeployMode.CLOUD:
        logging.info('部署模式为 %s ，初始化 SQLite 数据库', settings.dingding_deploy_mode)
        await REPO.create_all()

    logging.info('应用启动完成')


@app.on_event('shutdown')
async def shutdown():
    if settings.dingding_deploy_mode in (DeployMode.LOCAL, DeployMode.DEV_DEBUG):
        logging.warning('部署模式为 %s ，关闭 Postgres 数据库连接', settings.dingding_deploy_mode)
        await POSTGRES_ENGINE.dispose()
    elif settings.dingding_deploy_mode == DeployMode.CLOUD:
        logging.warning('部署模式为 %s ，关闭 SQLite 数据库连接', settings.dingding_deploy_mode)
        SQLITE_ENGINE.dispose()

    logging.info('应用关闭完成')
