import json
import logging
from typing import Any
from typing import Dict
from typing import Optional

import pendulum
from sqlalchemy import delete
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from tpdingding.helper.session import SQLITE_ENGINE
from tpdingding.helper.session import SQLiteSessionMaker
from tpdingding.model.entity import CorpAuth
from tpdingding.model.entity import CorpId
from tpdingding.model.entity import DingDingUser
from tpdingding.model.entity import Suite
from tpdingding.persistence.abstract import Repository
from tpdingding.persistence.model.orm import BaseOrm
from tpdingding.persistence.model.orm import CorpAuthOrm
from tpdingding.persistence.model.orm import SuiteOrm


class SQLiteRepository(Repository):
    """
    部署在云端，用 SqlLite 作为持久化存储
    存储 Suite 信息, 存储 CorpAuth 信息，存储用户信息（内存暂存）
    """

    def __init__(self, maker: SQLiteSessionMaker):
        self.session_maker = maker
        self.cache: Dict[str, DingDingUser] = {}

    @classmethod
    async def create_all(cls):
        with SQLITE_ENGINE.begin() as conn:
            BaseOrm.metadata.create_all(conn)

    async def save_org_suite_auth_info(self, corp_id: str, data: dict[str, Any]) -> bool:
        stmt = (
            insert(CorpAuthOrm)
            .values(
                corp_id=corp_id,
                permanent_code=data['permanent_code'],
                raw=json.dumps(data, ensure_ascii=False),
            )
            .on_conflict_do_update(
                index_elements=[CorpAuthOrm.corp_id],
                set_={
                    'raw': json.dumps(data, ensure_ascii=False),
                    'permanent_code': data['permanent_code'],
                    'updated_at': pendulum.now(),
                },
            )
        )
        self.session_maker().execute(stmt)
        return True

    async def relieve_org_suite_auth_info(self, corp_id: CorpId) -> bool:
        stmt = delete(CorpAuthOrm).where(CorpAuthOrm.corp_id == corp_id)
        self.session_maker().execute(stmt)
        return True

    async def get_org_suite_auth_info(self, corp_id: CorpId) -> Optional[CorpAuth]:
        stmt = select(CorpAuthOrm).where(CorpAuthOrm.corp_id == corp_id)
        result = self.session_maker().execute(stmt)
        data = result.scalar_one_or_none()
        return CorpAuth.from_orm(data) if data else None

    async def save_suite_ticket(self, suite: Suite) -> bool:
        stmt = (
            insert(SuiteOrm)
            .values(
                suite_ticket=suite.suite_ticket,
                corp_id=suite.corp_id,
                suite_key=suite.suite_key,
            )
            .on_conflict_do_update(
                index_elements=[SuiteOrm.corp_id],
                set_={
                    'suite_ticket': suite.suite_ticket,
                    'updated_at': pendulum.now(),
                },
            )
        )
        self.session_maker().execute(stmt)
        return True

    async def get_suite(self, suite_key: str) -> Optional[Suite]:
        stmt = select(SuiteOrm).where(SuiteOrm.suite_key == suite_key)
        result = self.session_maker().execute(stmt)
        data = result.scalar_one_or_none()
        return Suite.from_orm(data) if data else None

    async def save_user(self, auth_code: str, user: DingDingUser) -> bool:
        self.cache[auth_code] = user
        return True

    async def get_user_by_auth_code(self, auth_code: str) -> DingDingUser:
        if auth_code not in self.cache:
            raise ValueError(f"auth_code {auth_code} 不存在")
        user = self.cache.pop(auth_code)
        logging.warning("AuthCode %s 对应的用户信息已经被消费，不可重复使用", auth_code)
        return user

    # ==================== 以下方法 SQLiteRepository 不支持 ====================
    async def of_user_ids(self, user_ids: list[str]) -> list[DingDingUser]:
        raise NotImplementedError(f"{type(self).__name__} 不支持 of_user_ids 方法")
