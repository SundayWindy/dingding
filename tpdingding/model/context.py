from pydantic import BaseModel

from tpdingding.persistence.abstract import Repository
from tpdingding.service.dingding import DingDingService
from tpdingding.service.iam import IAMService


class Context(BaseModel):
    repo: Repository
    dingding_srv: DingDingService
    iam_srv: IAMService
    suite_key: str

    class Config:
        arbitrary_types_allowed = True
