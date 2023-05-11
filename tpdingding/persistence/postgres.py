import logging
from typing import Any
from typing import Optional
from urllib.parse import urljoin

import httpx
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from settings import BASIC_AUTH
from settings import settings
from tpdingding.exception import DingDingException
from tpdingding.helper.session import POSTGRES_ENGINE
from tpdingding.helper.session import PGSessionMaker
from tpdingding.model.entity import CorpAuth
from tpdingding.model.entity import DingDingId
from tpdingding.model.entity import DingDingUser
from tpdingding.model.entity import Suite
from tpdingding.persistence.abstract import Repository
from tpdingding.persistence.model.orm import BaseOrm
from tpdingding.persistence.model.orm import DingDingUserOrm


class PostgresRepository(Repository):
    """
    部署在本地，用 Postgres 作为持久化存储, 存储用户信息
    """

    def __init__(self, maker: PGSessionMaker):
        self.session_maker = maker

    @classmethod
    async def create_all(cls):
        async with POSTGRES_ENGINE.begin() as conn:
            await conn.run_sync(BaseOrm.metadata.create_all)

    async def of_user_ids(self, user_ids: list[DingDingId]) -> list[DingDingUser]:
        stmt = select(DingDingUserOrm).where(DingDingUserOrm.user_id.in_(user_ids))
        result = await self.session_maker().execute(stmt)
        data = result.scalars().all()
        return [DingDingUser.from_orm(d) for d in data]

    async def save_user(self, auth_code: str, user: DingDingUser) -> bool:
        logging.info("save_user of auth_code: %s", auth_code)
        stmt = (
            insert(DingDingUserOrm)
            .values(user.dict(exclude_unset=True))
            .on_conflict_do_update(
                constraint=DingDingUserOrm.uq_dingding_user_corp_id_user_id,
                set_=user.dict(exclude_unset=True),
            )
        )
        await self.session_maker().execute(stmt)

        return True

    # ==================== 以下方法 PostgresRepository 向云端数据库获取 ====================
    async def get_org_suite_auth_info(self, corp_id: str) -> Optional[CorpAuth]:
        async with AsyncClient() as client:
            response = await client.get(
                url=urljoin(
                    settings.dingding_cloud_host,
                    f"/dingding/internal/corp/{corp_id}",
                ),
                auth=BASIC_AUTH,
            )
            if response.status_code != httpx.codes.OK:
                raise DingDingException(f"获取企业授权信息失败: {response.text}")
            return CorpAuth(**response.json())

    async def get_suite(self, suite_key: str) -> Optional[Suite]:
        async with AsyncClient() as client:
            response = await client.get(
                url=urljoin(
                    settings.dingding_cloud_host,
                    f"/dingding/internal/suite/{suite_key}",
                ),
                auth=BASIC_AUTH,
            )
            if response.status_code != httpx.codes.OK:
                raise DingDingException(f"获取套件信息失败: {response.text}")
            return Suite(**response.json())

    async def get_user_by_auth_code(self, auth_code: str) -> DingDingUser:
        async with AsyncClient() as client:
            response = await client.get(
                url=urljoin(
                    settings.dingding_cloud_host,
                    f'/dingding/internal/user/{auth_code}',
                ),
                auth=BASIC_AUTH,
            )
            if response.status_code != httpx.codes.OK:
                raise DingDingException(f"获取用户信息失败: {response.text}")
            if not response.json():
                raise DingDingException(f"获取用户信息失败: 未找到用户信息 {auth_code}")
            return DingDingUser(**response.json())

    # ==================== 以下方法 PostgresRepository 不应该支持，数据在云端 ====================

    async def save_suite_ticket(self, suite: Suite) -> bool:
        raise NotImplementedError(f"{type(self).__name__} 不支持保存 save_suite_ticket 方法")

    async def save_org_suite_auth_info(self, corp_id: str, data: dict[str, Any]) -> bool:
        raise NotImplementedError(f"{type(self).__name__} 不支持保存企业授权信息 save_org_suite_auth_info 方法")

    async def relieve_org_suite_auth_info(self, corp_id: str) -> bool:
        raise NotImplementedError(f"{type(self).__name__} 不支持解除企业授权 relieve_org_suite_auth_info 方法")
