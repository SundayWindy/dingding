from __future__ import annotations

from collections.abc import Callable
from collections.abc import Generator
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.parse import ParseResult
from urllib.parse import parse_qsl
from urllib.parse import urlencode
from urllib.parse import urlparse

from pydantic import BaseSettings

ROOT_DIR = Path(__file__).parents[0]


class DeployMode(str, Enum):
    CLOUD = 'CLOUD'
    LOCAL = 'LOCAL'
    DEV_DEBUG = 'DEV_DEBUG'  # for local debug

    def __str__(self):
        return str(self.value)  # for better print


class AsyncPostgresDsn(str):
    @classmethod
    def __get_validators__(
        cls,
    ) -> Generator[Callable[[Any], AsyncPostgresDsn], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> AsyncPostgresDsn:
        url = urlparse(value)
        query_dict = dict(parse_qsl(url.query))

        query_string = urlencode([(k, v) for k, v in query_dict.items() if v is not None])
        new = ParseResult(
            'postgresql+asyncpg',
            url.netloc,
            url.path,
            url.params,
            query_string,
            url.fragment,
        )
        return AsyncPostgresDsn(new.geturl())


class Settings(BaseSettings):
    log_formatter: str = 'colored_console'
    log_level: str = 'INFO'
    database_url: AsyncPostgresDsn = 'postgresql://postgres:postgres@localhost:5432/dingding'
    sqlite_database_url: str = f'sqlite:////{ROOT_DIR}/sqlite.db?uri=true'
    umc_host: str = 'http://umc-be:8000'
    iam_host: str = 'http://iam-be:8000'

    dingding_aes_key: str = 'xxxxxx'
    dingding_token: str = 'xxxxxx'
    dingding_suit_key: str = 'xxxxxx'
    dingding_suite_secret: str = 'xxxxxx'
    dingding_template_id: str = 'xxxxxx'

    dingding_send_message_url = 'https://oapi.dingtalk.com/topapi/message/corpconversation/sendbytemplate'
    dingding_user_info_url: str = 'https://oapi.dingtalk.com/topapi/v2/user/getuserinfo'
    dingding_corp_token_url: str = "https://oapi.dingtalk.com/service/get_corp_token"
    dingding_cloud_host: str = 'https://dingding.ruicore.io'
    dingding_deploy_mode: DeployMode = DeployMode.LOCAL
    dingding_secret_user: str = 'ruicore'
    dingding_secret_password: str = 'xxxxxx'

    site_url: str = 'https://team.ruicore.io/login'
    root_dir: Path = ROOT_DIR

    class Config:
        env_file = str(ROOT_DIR / '.env')
        env_file_encoding = 'utf-8'
        env_prefix = ''


settings = Settings()

BASIC_AUTH = (
    settings.dingding_secret_user,
    settings.dingding_secret_password,
)
