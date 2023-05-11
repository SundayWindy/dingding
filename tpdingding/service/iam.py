from typing import Dict
from urllib.parse import urljoin

import httpx
from httpx import Headers

from tpdingding.exception import DingDingException
from tpdingding.model.entity import StaffId
from tpdingding.model.iam import BindDingdingUserInput
from tpdingding.model.iam import DingDingUserAccount


class IAMService:
    def __init__(self, host: str) -> None:
        self.host = host

    async def bind_ding_user(self, input: BindDingdingUserInput, headers: Headers) -> None:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                urljoin(self.host, '/api/internal/v1/iam/dingding/bind_user'),
                json=input.dict(),
                headers={'x-authenticated-userid': headers['x-authenticated-userid']},
            )
            if res.status_code != httpx.codes.OK:
                raise DingDingException(res.json()['message'])

    async def list_dingding_users(self, staff_ids: list[StaffId]) -> Dict[StaffId, DingDingUserAccount]:
        async with httpx.AsyncClient() as client:
            res = await client.request(
                "GET",
                urljoin(self.host, '/api/internal/v1/iam/dingding/staff_dingding_user_map'),
                json=staff_ids,
            )
            if res.status_code != httpx.codes.OK:
                raise DingDingException(f'向 IAM 批量获取用户信息失败 {res.text}')
            data = res.json()
            return {key: DingDingUserAccount(**v) for key, v in data.items()}
