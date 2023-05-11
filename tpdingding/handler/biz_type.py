import json
import logging
from enum import Enum
from typing import Any

from tpdingding.model.context import Context
from tpdingding.model.entity import Suite
from tpdingding.model.event import SyncAction

BIZ_TYPE_HANDLER_MAP = {}


class BizType(int, Enum):
    ORG_SUITE_AUTH = 4  # 授权企业
    SUITE_TICKET = 2
    DEFAULT = -1


def biz_handler_register(type_: BizType):
    def decorator(func):
        BIZ_TYPE_HANDLER_MAP[type_] = func
        return func

    return decorator


@biz_handler_register(BizType.DEFAULT)
async def _default_handler(_: Context, msg: dict[str, Any]) -> bool:
    logging.warning('No handler for msg %s', msg)
    return True


@biz_handler_register(BizType.SUITE_TICKET)
async def handle_suite_ticket(ctx: Context, data: dict[str, Any]) -> bool:
    biz_data = json.loads(data['biz_data'])
    await ctx.repo.save_suite_ticket(
        Suite(
            corp_id=data['corp_id'],
            suite_ticket=biz_data['suiteTicket'],
            suite_key=ctx.suite_key,
        )
    )
    ctx.dingding_srv.refresh_suite(corp_id=data['corp_id'], suite_ticket=biz_data['suiteTicket'])
    return True


@biz_handler_register(BizType.ORG_SUITE_AUTH)
async def handle_org_suite_auth(ctx: Context, data: dict[str, Any]) -> bool:
    corp_id = data['corp_id']
    biz_data = json.loads(data['biz_data'])
    sync_action = biz_data['syncAction'].upper()
    if sync_action == SyncAction.ORG_SUITE_AUTH:
        await ctx.repo.save_org_suite_auth_info(corp_id, biz_data)
    elif sync_action == SyncAction.ORG_SUITE_RELIEVE:
        await ctx.repo.relieve_org_suite_auth_info(corp_id)
    else:
        raise Exception(f'Unknown sync action {sync_action}')  # pylint: disable=broad-exception-raised
    logging.info('handle_org_suite_auth: %s', biz_data)
    return True


async def handle_biz_types(ctx: Context, msg: dict[str, Any]) -> bool:
    for biz_data in msg['bizData']:
        biz_type = biz_data['biz_type']
        if biz_type in BizType.__members__.values():
            handler = BIZ_TYPE_HANDLER_MAP[BizType(biz_type)]
        else:
            handler = BIZ_TYPE_HANDLER_MAP[BizType.DEFAULT]

        await handler(ctx, biz_data)

    return True
