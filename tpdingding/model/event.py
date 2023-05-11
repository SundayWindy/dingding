from enum import Enum

from pydantic import BaseModel


class EventType(str, Enum):
    CHECK_URL = 'CHECK_URL'
    CHECK_UPDATE_SUITE_URL = 'CHECK_UPDATE_SUITE_URL'
    SYNC_HTTP_PUSH_HIGH = 'SYNC_HTTP_PUSH_HIGH'
    SYNC_HTTP_PUSH_MEDIUM = 'SYNC_HTTP_PUSH_MEDIUM'
    DEFAULT = 'DEFAULT'


class SyncAction(str, Enum):
    ORG_SUITE_RELIEVE = 'ORG_SUITE_RELIEVE'
    ORG_SUITE_AUTH = 'ORG_SUITE_AUTH'


class GrantType(str, Enum):
    AUTHORIZATION_CODE = 'authorization_code'
    REFRESH_TOKEN = 'refresh_token'


class EventSuccessReceived(BaseModel):
    msg_signature: str
    timeStamp: str
    nonce: str
    encrypt: str
