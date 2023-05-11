import json
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from dataclasses import field
from logging import Formatter
from logging import LogRecord
from logging import setLogRecordFactory
from logging.config import dictConfig

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import DispatchFunction
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from settings import Settings

REQUEST_ID_HEADER = 'x-request-id'
USER_ID_HEADER = 'x-authenticated-userid'
REQUEST_ID_CTX = ContextVar('request_id', default='N/A')
USER_ACCOUNT_CTX = ContextVar('user_account', default='N/A')


class JSONFormatter(Formatter):
    default_time_format = '%Y-%m-%d %H:%M:%S.%%03d %z'
    attrs = ['request_id', 'user_account', 'name', 'levelname', 'process']

    def format(self, record: LogRecord) -> str:
        data = {attr: record.__dict__.get(attr) for attr in self.attrs}
        data['message'] = record.getMessage()
        data['asctime'] = self.formatTime(record, self.default_time_format) % record.msecs
        if record.exc_info:
            data['exc_text'] = self.formatException(record.exc_info).splitlines()
        if record.stack_info:
            data['stack_info'] = self.formatStack(record.stack_info)
        return json.dumps(data, ensure_ascii=False, indent=2)


class LogExtraFactory(LogRecord):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request_id = REQUEST_ID_CTX.get() or 'N/A'
        user_account = USER_ACCOUNT_CTX.get() or 'N/A'
        self.__dict__['request_id'] = request_id
        self.__dict__['user_account'] = user_account


def init_logger(settings: Settings):
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {'class': 'tpdingding.middleware.track.JSONFormatter'},
            'simple': {'format': '[%(asctime)s] [%(levelname)s] [%(message)s]'},
            'colored_console': {
                '()': 'colorlog.ColoredFormatter',
                'format': '%(log_color)s%(asctime)s.%(msecs)03d '
                '- %(request_id)s '
                '- %(user_account)s '
                '- %(name)s '
                '- %(levelname)s '
                '- %(process)d '
                '- %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S',
                'log_colors': {
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                },
            },
        },
        'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': settings.log_formatter}},
        'root': {'level': settings.log_level, 'handlers': ['console']},
        'loggers': {
            'tpdingding': {'level': settings.log_level, 'handlers': ['console'], 'propagate': False},
            'databases': {'level': settings.log_level, 'handlers': ['console'], 'propagate': False},
            'uvicorn': {'handlers': ['console'], 'level': settings.log_level, 'propagate': False},
            'uvicorn.error': {'level': settings.log_level, 'handlers': ['console'], 'propagate': False},
            'uvicorn.access': {'handlers': ['console'], 'level': settings.log_level, 'propagate': False},
        },
    }
    dictConfig(config)
    setLogRecordFactory(LogExtraFactory)

    return config


@dataclass
class RequestIdMiddleware(BaseHTTPMiddleware):
    app: ASGIApp
    id_header: str = REQUEST_ID_HEADER
    dispatch_func: DispatchFunction = field(init=False)

    def __post_init__(self):
        self.dispatch_func = self.dispatch

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(self.id_header, str(uuid.uuid4()))
        REQUEST_ID_CTX.set(request_id)

        user_info = request.headers.get(USER_ID_HEADER)
        if (not user_info) or (user_info == 'undefined'):
            user_info = '{}'
        account = json.loads(user_info).get('account')
        USER_ACCOUNT_CTX.set(account)

        response = await call_next(request)
        response.headers[self.id_header] = request_id

        return response
