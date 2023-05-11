"""用于钉钉回调的 云端Router"""
import json
import logging
from typing import Optional

import httpx
from fastapi import Depends
from fastapi import Query
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.responses import Response

from crypto import DingCallbackCrypto3
from settings import settings
from tpdingding.exception import DingDingException
from tpdingding.handler.handle import handle_event
from tpdingding.helper.dependencies import get_context
from tpdingding.helper.dependencies import login
from tpdingding.model.context import Context
from tpdingding.model.entity import CloudSendMessageInput
from tpdingding.model.entity import CorpAuth
from tpdingding.model.entity import CorpId
from tpdingding.model.entity import DingDingUser
from tpdingding.model.entity import Suite
from tpdingding.model.event import EventSuccessReceived
from tpdingding.persistence.sqlite import SQLiteRepository
from tpdingding.router import router

DOMAIN_DELIMITER = '::'


@router.post('/dingding/event/pushed', summary='钉钉事件推送', tags=['钉钉事件回调'])
async def event_callback(
    request: Request,
    msg_signature: str = Query(description="消息签名"),
    timestamp: str = Query(description="时间戳"),
    nonce: str = Query(description="随机数"),
    ctx: Context = Depends(get_context),
) -> EventSuccessReceived:
    data = await request.json()
    dtc = DingCallbackCrypto3(
        settings.dingding_token,
        settings.dingding_aes_key,
        settings.dingding_suit_key,
    )
    msg = dtc.get_decrypt_msg(msg_signature, timestamp, nonce, data['encrypt'])
    await handle_event(ctx, json.loads(msg))
    return EventSuccessReceived(**dtc.get_encrypted_map('success'))


@router.get(
    '/dingding/auth/user/callback',
    summary='钉钉用户授权回调',
    tags=['钉钉用户授权'],
)
async def auth_user_callback(
    state: str = Query(description="验证是否是同一请求"),
    auth_code: str = Query(alias='authCode'),
    ctx: Context = Depends(get_context),
) -> Response:
    logging.info('auth_user_callback: %s, %s', state, auth_code)
    dingding_user = await ctx.dingding_srv.get_user_info(auth_code)

    assert isinstance(ctx.repo, SQLiteRepository), '云端部署使用 SQLiteRepository'

    await ctx.repo.save_user(auth_code, dingding_user)
    if len(state.split(DOMAIN_DELIMITER)) != 2:
        raise DingDingException("state 参数错误不符合约定")
    logging.info("根据 auth_code 获取用户信息 %s %s", auth_code, dingding_user.user_id)
    return RedirectResponse(url=f'{state.split(DOMAIN_DELIMITER)[0]}/profile?state={state}&authCode={auth_code}')


@router.get(
    '/dingding/internal/user/{auth_code}',
    summary='根据 auth_code 获取用户信息',
    tags=['内部调用接口'],
    response_model=Optional[DingDingUser],
)
async def get_user_by_auth_code(
    auth_code: str,
    ctx: Context = Depends(get_context),
    _: str = Depends(login),
) -> Optional[DingDingUser]:
    return await ctx.repo.get_user_by_auth_code(auth_code)


@router.get(
    '/dingding/internal/corp/{corp_id}',
    summary='获取企业信息',
    tags=['内部调用接口'],
    response_model=Optional[CorpAuth],
)
async def get_corp_info(
    corp_id: CorpId,
    ctx: Context = Depends(get_context),
    _: str = Depends(login),
) -> Optional[CorpAuth]:
    return await ctx.repo.get_org_suite_auth_info(corp_id)


@router.get(
    '/dingding/internal/suite/{suite_key}',
    summary='获取套件信息',
    tags=["内部调用接口"],
    response_model=Optional[Suite],
)
async def get_suite_info(
    suite_key: str,
    ctx: Context = Depends(get_context),
    _: str = Depends(login),
) -> Optional[Suite]:
    assert suite_key == ctx.suite_key, 'suite_key 不匹配'
    return await ctx.dingding_srv.get_suite()  # 作为平台，只有一家，所以直接返回


@router.post('/dingding/internal/send/messages', summary='发送钉钉消息', tags=['内部调用接口'])
async def cloud_send_messages(
    message: CloudSendMessageInput,
    ctx: Context = Depends(get_context),
    _: str = Depends(login),
) -> Response:
    await ctx.dingding_srv.send_message(message.user_ids, message.message, message.corp_id)
    return Response(status_code=httpx.codes.OK, content='success')
