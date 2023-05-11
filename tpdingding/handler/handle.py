import logging
from typing import Any

from tpdingding.handler.biz_type import handle_biz_types
from tpdingding.model.context import Context
from tpdingding.model.event import EventType

EVENT_HANDLER_MAP = {}


def register_handler(type_: str):
    def decorator(func):
        EVENT_HANDLER_MAP[type_] = func
        return func

    return decorator


@register_handler(EventType.DEFAULT)
async def _default_handler(_: Context, msg: dict[str, Any]) -> bool:
    logging.warning('No handler for event type %s', msg['EventType'])
    return True


@register_handler(EventType.CHECK_URL)
async def handle_check_url(_: Context, msg: dict[str, Any]) -> bool:
    logging.info('handle_check_url: %s', msg)
    return True


@register_handler(EventType.CHECK_UPDATE_SUITE_URL)
async def handle_check_update_suite_url(_: Context, msg: dict[str, Any]) -> bool:
    logging.info('handle_check_update_suite_url: %s', msg)
    return True


@register_handler(EventType.SYNC_HTTP_PUSH_HIGH)
@register_handler(EventType.SYNC_HTTP_PUSH_MEDIUM)
async def handle_sync_http_push(ctx: Context, msg: dict[str, Any]) -> bool:
    await handle_biz_types(ctx, msg)
    return True


async def handle_event(ctx: Context, msg: dict[str, Any]) -> bool:
    event_type = msg['EventType'].upper()
    handler = EVENT_HANDLER_MAP.get(event_type, EVENT_HANDLER_MAP[EventType.DEFAULT])
    return await handler(ctx, msg)
