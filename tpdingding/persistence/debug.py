"""This Repository is a hybrid of the two repositories <Postgres & Sqlite>, which is used to debug the application."""
import json
import logging
from typing import Any
from typing import Optional

import pendulum
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from tpdingding.helper.session import PGSessionMaker
from tpdingding.model.entity import CorpAuth
from tpdingding.model.entity import DingDingUser
from tpdingding.model.entity import Suite
from tpdingding.persistence.model.orm import CorpAuthOrm
from tpdingding.persistence.model.orm import SuiteOrm
from tpdingding.persistence.postgres import PostgresRepository


class HybridRepository(PostgresRepository):
    def __init__(self, maker: PGSessionMaker):
        super().__init__(maker)
        self.cache = {}

    async def save_suite_ticket(self, suite: Suite) -> bool:
        stmt = (
            insert(SuiteOrm)
            .values(
                suite_ticket=suite.suite_ticket,
                corp_id=suite.corp_id,
                suite_key=suite.suite_key,
            )
            .on_conflict_do_update(
                constraint=SuiteOrm.uq_suite_ticket_corp_id,
                set_={
                    'suite_ticket': suite.suite_ticket,
                    'updated_at': pendulum.now(),
                },
            )
        )
        await self.session_maker().execute(stmt)
        return True

    async def get_suite(self, suite_key: str) -> Optional[Suite]:
        stmt = select(SuiteOrm).where(SuiteOrm.suite_key == suite_key)
        result = await self.session_maker().execute(stmt)
        data = result.scalar_one_or_none()

        return Suite.from_orm(data) if data else None

    async def save_org_suite_auth_info(self, corp_id: str, data: dict[str, Any]) -> bool:
        stmt = (
            insert(CorpAuthOrm)
            .values(
                corp_id=corp_id,
                permanent_code=data['permanent_code'],
                raw=json.dumps(data),
            )
            .on_conflict_do_update(
                constraint=CorpAuthOrm.uq_corp_auth_corp_id,
                set_={
                    'raw': json.dumps(data, ensure_ascii=False),
                    'permanent_code': data['permanent_code'],
                    'updated_at': pendulum.now(),
                },
            )
        )
        await self.session_maker().execute(stmt)
        return True

    async def relieve_org_suite_auth_info(self, corp_id: str) -> bool:
        stmt = delete(CorpAuthOrm).where(CorpAuthOrm.corp_id == corp_id)
        await self.session_maker().execute(stmt)
        return True

    async def get_org_suite_auth_info(self, corp_id: str) -> Optional[CorpAuth]:
        stmt = select(CorpAuthOrm).where(CorpAuthOrm.corp_id == corp_id)
        result = await self.session_maker().execute(stmt)
        return result.scalar_one_or_none()

    async def save_user(self, auth_code: str, user: DingDingUser) -> bool:
        await super().save_user(auth_code, user)
        self.cache[auth_code] = user
        return True

    async def get_user_by_auth_code(self, auth_code: str) -> DingDingUser:
        if auth_code not in self.cache:
            raise ValueError(f"auth_code {auth_code} 不存在")
        user = self.cache[auth_code]
        self.cache.pop(auth_code, None)
        logging.warning("AuthCode  %s 对应的用户信息已经被消费，不可重复使用", auth_code)
        return user
