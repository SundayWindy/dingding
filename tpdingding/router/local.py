"""执行处理在内网服务器上的 Router"""

import json
import logging
from urllib.parse import urljoin

import httpx
import pendulum
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi import Response

from settings import BASIC_AUTH
from settings import settings
from tpdingding.exception import DingDingException
from tpdingding.helper.dependencies import get_context
from tpdingding.model.context import Context
from tpdingding.model.entity import CloudSendMessageInput
from tpdingding.model.entity import SendMessageInput
from tpdingding.model.entity import StaffId
from tpdingding.model.entity import TenantId
from tpdingding.model.iam import BindDingdingUserInput
from tpdingding.persistence.postgres import PostgresRepository
from tpdingding.router import router


@router.get('/dingding/local/auth/user/callback', summary='后置钉钉用户授权回调', tags=['钉钉用户授权'])
async def auth_user_callback(
    request: Request,
    staff_id: StaffId = Query(description="IAM 平台的 StaffId"),
    tenant_id: TenantId = Query(description="IAM 平台的 TenantId"),
    auth_code: str = Query(description="钉钉授权码"),
    ctx: Context = Depends(get_context),
):
    assert isinstance(ctx.repo, PostgresRepository), '本地部署使用 PostgresRepository'
    dingding_user = await ctx.repo.get_user_by_auth_code(auth_code)
    dingding_user.staff_id = staff_id
    dingding_user.tenant_id = tenant_id

    await ctx.repo.save_user(auth_code, dingding_user)
    await ctx.iam_srv.bind_ding_user(
        BindDingdingUserInput(
            staff_id=staff_id,
            tenant_id=tenant_id,
            dingding_id=dingding_user.user_id,
            name=dingding_user.nick,
        ),
        headers=request.headers,
    )
    return Response(status_code=httpx.codes.OK, content='success')


@router.post('/dingding/local/send/messages', summary='发送钉钉消息', tags=['钉钉消息推送'])
async def send_messages(
    _: Request,
    message: SendMessageInput,
    ctx: Context = Depends(get_context),
) -> Response:
    assert isinstance(ctx.repo, PostgresRepository), '本地部署使用 PostgresRepository'
    logging.info("尝试为租户为 %s 的 staff %s 发送消息", message.tenant_id, message.staff_ids)

    # 获取用户
    iam_registered_dingding_users = await ctx.iam_srv.list_dingding_users(message.staff_ids)
    # logging.info("IAM 平台已注册的钉钉用户: %s", iam_registered_dingding_users)
    user_ids_to_send, user_ids_missing = [], []
    for staff_id in message.staff_ids:
        if staff_id not in iam_registered_dingding_users:
            user_ids_missing.append(staff_id)
        else:
            user_ids_to_send.append(iam_registered_dingding_users[staff_id].dingding_id)

    if not user_ids_to_send:
        logging.warning("没有找到任何用户")
        return Response(status_code=httpx.codes.NOT_FOUND, content='没有找到任何用户')

    if user_ids_missing:
        logging.warning('尝试发送消息，未找到部分用户: %s ', user_ids_missing)

    # 发送消息
    local_dingding_users = await ctx.repo.of_user_ids(user_ids_to_send)  # 为了拿到 corp_id
    # logging.info("本地已注册的钉钉用户: %s", local_dingding_users)
    if not local_dingding_users:
        raise DingDingException('没有找到 corp_id')

    logging.info('Final: 尝试发送消息给 %s', user_ids_to_send)

    # 钉钉消息模版使用 message 作为消息变量
    # 钉钉消息模版使用 url 作为跳转地址
    async with httpx.AsyncClient() as client:
        response = await client.post(
            urljoin(settings.dingding_cloud_host, '/dingding/internal/send/messages'),
            json=CloudSendMessageInput(
                corp_id=local_dingding_users[0].corp_id,
                user_ids=user_ids_to_send,
                message=json.dumps(
                    {
                        'message': message.data + f'\n{pendulum.now().strftime("%Y-%m-%d %H:%M:%S")}',
                        'url': message.url or settings.site_url,
                    }
                ),
            ).dict(),
            auth=BASIC_AUTH,
        )
        if response.status_code != httpx.codes.OK:
            raise DingDingException(f"发送消息失败 {response.text}")

    return Response(status_code=httpx.codes.OK, content='success')
