from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from settings import settings


class StaffId(str):
    ...


class AccountId(str):
    ...


class TenantId(str):
    ...


class UserId(str):
    """https://open.dingtalk.com/document/org/basic-concepts"""


class UnionId(str):
    """https://open.dingtalk.com/document/org/basic-concepts"""


class CorpId(str):
    """https://open.dingtalk.com/document/org/basic-concepts"""


class AgentId(str):
    """https://open.dingtalk.com/document/org/basic-concepts"""


class OpenId(str):
    ...


DingDingId = UserId


class Suite(BaseModel):
    corp_id: CorpId
    suite_key: str
    suite_ticket: str

    class Config:
        orm_mode = True


class CorpAuth(BaseModel):
    corp_id: CorpId
    permanent_code: str
    raw: str  # json dump str

    class Config:
        orm_mode = True


class DingDingUserInput(BaseModel):
    nick: str
    corp_id: CorpId
    open_id: OpenId = Field(alias='openId')
    union_id: UnionId = Field(alias='unionId')

    # user_id 通过 union_id 获取
    user_id: Optional[UserId]

    email: Optional[str]
    avatar_url: Optional[str] = Field(alias='avatarUrl')
    mobile: Optional[str]

    # IAM 平台的绑定信息
    staff_id: Optional[StaffId]
    tenant_id: Optional[TenantId]


class DingDingUser(BaseModel):
    nick: str
    corp_id: CorpId
    open_id: OpenId
    union_id: UnionId

    # user_id 通过 union_id 获取
    user_id: Optional[UserId]

    email: Optional[str]
    avatar_url: Optional[str]
    mobile: Optional[str]

    # IAM 平台的绑定信息
    staff_id: Optional[StaffId]
    tenant_id: Optional[TenantId]

    class Config:
        orm_mode = True


class SendMessageInput(BaseModel):
    staff_ids: list[StaffId] = Field(description='IAM 平台的 StaffId')
    tenant_id: TenantId = Field(description='IAM 平台的 TenantId')
    data: str = Field(
        description='字符串, 详情请参考钉钉文档的 Body 参数 '
        'https://open.dingtalk.com/document/isvapp-server/work-notification-templating-send-notification-interface'
    )
    url: Optional[str] = Field(
        description='消息点击链接地址, 当为空时在钉钉客户端将无法点击消息打开链接',
        default=settings.site_url,
    )


class CloudSendMessageInput(BaseModel):
    corp_id: CorpId = Field(description='钉钉企业 ID')
    user_ids: list[UserId] = Field(description='钉钉用户 ID')
    message: str = Field(description='消息内容')
