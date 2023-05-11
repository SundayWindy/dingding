from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from settings import settings
from tpdingding.middleware.deploy import REPO
from tpdingding.model.context import Context
from tpdingding.service.dingding import DingDingService
from tpdingding.service.iam import IAMService

DINGDING_SRV = DingDingService(
    suite_key=settings.dingding_suit_key,
    suite_secret=settings.dingding_suite_secret,
    repo=REPO,
    corp_token_url=settings.dingding_corp_token_url,
    send_message_url=settings.dingding_send_message_url,
    template_id=settings.dingding_template_id,
)
IAM_SRV = IAMService(host=settings.iam_host)


class ContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.context = Context(
            repo=REPO,
            suite_key=settings.dingding_suit_key,
            dingding_srv=DINGDING_SRV,
            iam_srv=IAM_SRV,
        )
        return await call_next(request)
