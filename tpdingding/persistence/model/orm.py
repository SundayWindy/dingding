from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy import func
from sqlalchemy.orm import declarative_base

from tpdingding.model.entity import CorpAuth
from tpdingding.model.entity import DingDingUser
from tpdingding.model.entity import Suite

BaseOrm = declarative_base()


class TimeMixIn:
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now, onupdate=func.now)


class IDMixIn:
    id = Column(Integer, primary_key=True)


class SuiteOrm(BaseOrm, IDMixIn, TimeMixIn):
    __tablename__ = 'suite'
    __pydantic_model__ = Suite

    corp_id = Column(String, nullable=False)
    suite_key = Column(String, nullable=False)
    suite_ticket = Column(String, nullable=False)

    uq_suite_ticket_corp_id = UniqueConstraint(
        'corp_id',
        name='uq_suite_corp_id',
    )
    __table_args__ = (uq_suite_ticket_corp_id,)


class CorpAuthOrm(BaseOrm, IDMixIn, TimeMixIn):
    __tablename__ = 'corp_auth'
    __pydantic_model__ = CorpAuth

    corp_id = Column(String, nullable=False)
    permanent_code = Column(String, nullable=False)
    raw = Column(String, nullable=False)

    uq_corp_auth_corp_id = UniqueConstraint(
        'corp_id',
        name='uq_suite_auth_corp_id',
    )
    __table_args__ = (uq_corp_auth_corp_id,)


class DingDingUserOrm(BaseOrm, IDMixIn, TimeMixIn):
    # https://m.dingtalk.com/qidian/help-detail-1000103589

    __tablename__ = 'dingding_user'
    __pydantic_model__ = DingDingUser

    nick = Column(String, nullable=False)
    corp_id = Column(String, nullable=False)
    open_id = Column(String, nullable=False)
    union_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)

    # 用户其他信息
    email = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    mobile = Column(String, nullable=True)

    # IAM 平台的绑定信息
    staff_id = Column(String, nullable=True)
    tenant_id = Column(String, nullable=True)

    uq_dingding_user_corp_id_user_id = UniqueConstraint(
        'corp_id',
        'user_id',
        name='uq_dingding_user_corp_id_union_id',
    )
    __table_args__ = (uq_dingding_user_corp_id_user_id,)
