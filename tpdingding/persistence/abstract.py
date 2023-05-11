from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Optional

from tpdingding.model.entity import CorpAuth
from tpdingding.model.entity import DingDingUser
from tpdingding.model.entity import Suite


class Repository(ABC):
    @classmethod
    async def create_all(cls):
        ...

    @abstractmethod
    async def save_suite_ticket(self, suite: Suite) -> bool:
        ...

    @abstractmethod
    async def get_suite(self, suite_key: str) -> Optional[Suite]:
        ...

    @abstractmethod
    async def save_org_suite_auth_info(self, corp_id: str, data: dict[str, Any]) -> bool:
        ...

    @abstractmethod
    async def relieve_org_suite_auth_info(self, corp_id: str) -> bool:
        ...

    @abstractmethod
    async def get_org_suite_auth_info(self, corp_id: str) -> Optional[CorpAuth]:
        ...

    @abstractmethod
    async def of_user_ids(self, user_ids: list[str]) -> list[DingDingUser]:
        ...

    @abstractmethod
    async def save_user(self, auth_code: str, user: DingDingUser) -> bool:
        ...

    @abstractmethod
    async def get_user_by_auth_code(self, auth_code: str) -> DingDingUser:
        ...
