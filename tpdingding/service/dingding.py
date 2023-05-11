import base64
import hashlib
import hmac
import json
import logging
from typing import Optional

import httpx
import pendulum
from alibabacloud_dingtalk.contact_1_0 import models as dingtalkcontact__1__0_models
from alibabacloud_dingtalk.contact_1_0.client import Client as dingtalkcontact_1_0Client
from alibabacloud_dingtalk.contact_1_0.models import GetUserResponse
from alibabacloud_dingtalk.oauth2_1_0 import models as dingtalkoauth_2__1__0_models
from alibabacloud_dingtalk.oauth2_1_0.client import Client as dingtalkoauth2_1_0Client
from alibabacloud_dingtalk.oauth2_1_0.models import GetUserTokenResponse
from alibabacloud_dingtalk.oauth2_1_0.models import GetUserTokenResponseBody
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_util.client import Client as UtilClient
from httpx import AsyncClient
from Tea.exceptions import TeaException

from settings import DeployMode
from settings import settings
from tpdingding.exception import DingDingException
from tpdingding.model.entity import AgentId
from tpdingding.model.entity import CorpId
from tpdingding.model.entity import DingDingUser
from tpdingding.model.entity import DingDingUserInput
from tpdingding.model.entity import Suite
from tpdingding.model.entity import UnionId
from tpdingding.model.entity import UserId
from tpdingding.model.event import GrantType
from tpdingding.model.token import AccessToken
from tpdingding.persistence.abstract import Repository
from tpdingding.persistence.postgres import PostgresRepository


class DingDingService:
    suite_key: str
    suite_secret: str
    repo: Repository

    def __init__(
        self,
        suite_key: str,
        suite_secret: str,
        repo: Repository,
        corp_token_url: str,
        send_message_url: str,
        template_id: str,
    ):
        self.suite_key: str = suite_key
        self.suite_secret: str = suite_secret
        self.repo: Repository = repo
        self.corp_token_url = corp_token_url
        self.send_message_url = send_message_url
        self.template_id = template_id

        self._provider_corp_id: Optional[CorpId] = None
        self._suite: Optional[Suite] = None
        self._corp_tokens: dict[CorpId, AccessToken] = {}
        self._suite_access_token: Optional[AccessToken] = None
        self._corp_agent_id: dict[CorpId, AgentId] = {}  # TODO: 暂时假定一个企业只有一个应用

    def refresh_suite(self, corp_id: CorpId, suite_ticket: str) -> None:
        self._provider_corp_id = corp_id
        self._suite = Suite(
            corp_id=corp_id,
            suite_key=self.suite_key,
            suite_ticket=suite_ticket,
        )

    async def get_suite(self) -> Suite:
        if settings.dingding_deploy_mode == DeployMode.LOCAL:
            # LOCAL 部署模式，一定要向云端获取套件信息
            assert isinstance(self.repo, PostgresRepository)
            suite = await self.repo.get_suite(self.suite_key)
            if suite is None:
                raise DingDingException(f"没有找到 suite_key 为 {self.suite_key} 的套件")
            return suite

        if self._suite is None:
            self._suite = await self.repo.get_suite(self.suite_key)

        if self._suite is None:
            raise DingDingException(f"没有找到 suite_key 为 {self.suite_key} 的套件")

        return self._suite

    async def send_message(self, user_ids: list[UserId], message: str, corp_id: CorpId) -> bool:
        """
        message 是发送的内容，可以为 json dumps 的字符串

        https://open.dingtalk.com/document/isvapp-server/work-notification-templating-send-notification-interface
        """
        async with AsyncClient() as client:
            response = await client.post(
                url=self.send_message_url,
                params={
                    "access_token": await self.get_corp_token(corp_id),
                },
                json={
                    "agent_id": await self._get_corp_agent_id(corp_id),
                    "userid_list": ','.join(user_ids),
                    "template_id": self.template_id,
                    "data": message,
                },
            )
            if response.status_code != httpx.codes.OK or response.json()['errcode'] != 0:
                raise DingDingException(
                    f"发送钉钉消息失败,状态码:{response.status_code}, 返回内容:{response.text}",
                )
            logging.info("发送钉钉消息成功 %s", response.text)

        return True

    async def get_corp_token(self, corp_id: CorpId) -> str:
        """
        获取企业凭证

        https://developer.work.weixin.qq.com/document/path/90605
        """
        if (token := self._corp_tokens.get(corp_id)) and not token.is_expired():
            return token.value

        async with AsyncClient() as client:
            timestamp = int(pendulum.now().timestamp() * 1000)
            response = await client.post(
                url=self.corp_token_url,
                params={
                    "accessKey": self.suite_key,
                    'timestamp': timestamp,
                    'suiteTicket': await self._get_suite_ticket(),
                    'signature': await self._get_signature(timestamp),
                },
                json={'auth_corpid': corp_id},
            )
            if response.status_code != httpx.codes.OK:
                raise DingDingException(f"获取企业内 {corp_id} 凭证失败,状态码:{response.status_code},返回内容:{response.text}")

            data = response.json()
            if (errcode := data.get('errcode', 0)) and errcode != 0:
                raise DingDingException(f"获取企业内 {corp_id} 凭证失败, 响应内容: {data}")

            token = AccessToken(data['access_token'], data['expires_in'])
            self._corp_tokens[corp_id] = token

            return token.value

    async def get_suite_access_token(self) -> str:
        # https://open.dingtalk.com/document/isvapp-server/obtains-the-suite_acess_token-of-third-party-enterprise-applications
        if self._suite_access_token is not None and not self._suite_access_token.is_expired():
            return self._suite_access_token.value

        client = dingtalkoauth2_1_0Client(open_api_models.Config(protocol='https', region_id='central'))
        get_corp_access_token_request = dingtalkoauth_2__1__0_models.GetCorpAccessTokenRequest(
            suite_key=self.suite_key,
            suite_secret=self.suite_secret,
            auth_corp_id=await self._get_auth_corp_id(),
            suite_ticket=await self._get_suite_ticket(),
        )
        try:
            response = await client.get_corp_access_token_async(get_corp_access_token_request)
            self._suite_access_token = AccessToken(
                value=response.body.access_token,
                expires_in=response.body.expire_in,
            )
            return self._suite_access_token.value

        except TeaException as err:
            if not UtilClient.empty(err.code) and not UtilClient.empty(err.message):
                logging.warning("Get access token error of code %s and message %s", err.code, err.message)
                raise

    async def _get_signature(self, timestamp: int) -> str:
        string_to_sign = f"{timestamp}\n{await self._get_suite_ticket()}"
        signature = hmac.new(
            bytes(self.suite_secret, 'UTF-8'),
            msg=bytes(string_to_sign, 'UTF-8'),
            digestmod=hashlib.sha256,
        ).digest()

        return base64.b64encode(signature).decode()

    async def _get_corp_agent_id(self, corp_id: CorpId) -> AgentId:
        if corp_id not in self._corp_agent_id:
            logging.warning("corp 的 agent_id 没有被缓存，调用 repo 获取")
            corp_auth_info = await self.repo.get_org_suite_auth_info(corp_id)
            if corp_auth_info is None:
                raise Exception(f"企业 {corp_id} 授权信息没有被授权此应用")  # pylint: disable=broad-exception-raised
            raw = json.loads(corp_auth_info.raw)
            self._corp_agent_id[corp_id] = raw['auth_info']['agent'][0]['agentid']

        return self._corp_agent_id[corp_id]

    async def _get_auth_corp_id(self) -> CorpId:
        if self._provider_corp_id:
            return self._provider_corp_id

        return (await self.get_suite()).corp_id

    async def _get_suite_ticket(self) -> str:
        return (await self.get_suite()).suite_ticket

    async def get_user_info(self, auth_code: str) -> DingDingUser:
        # https://open.dingtalk.com/document/isvapp-server/dingtalk-retrieve-user-information
        client = dingtalkcontact_1_0Client(open_api_models.Config(protocol='https', region_id='central'))
        get_user_headers = dingtalkcontact__1__0_models.GetUserHeaders()
        token = await self._get_user_token(auth_code)
        get_user_headers.x_acs_dingtalk_access_token = token.access_token
        try:
            response: GetUserResponse = await client.get_user_with_options_async(
                'me',
                get_user_headers,
                util_models.RuntimeOptions(),
            )
        except TeaException as err:
            if not UtilClient.empty(err.code) and not UtilClient.empty(err.message):
                raise DingDingException(f'Get user info error of code {err.code} and message {err.message}') from err
            raise

        if token.corp_id is None:
            raise DingDingException('根据 auth_code 获取的用户信息中没有 corp_id')
        dingding_user = DingDingUserInput(**response.body.to_map(), corp_id=CorpId(token.corp_id))
        dingding_user.user_id = await self._get_userid_by_unionid(dingding_user.union_id, dingding_user.corp_id)

        return DingDingUser(**dingding_user.dict())

    async def _get_user_token(self, auth_code: str) -> GetUserTokenResponseBody:
        """通过OAuth Code 获取用户授权的 access_token"""
        client = dingtalkoauth2_1_0Client(open_api_models.Config(protocol='https', region_id='central'))
        get_user_token_request = dingtalkoauth_2__1__0_models.GetUserTokenRequest(
            client_id=self.suite_key,
            client_secret=self.suite_secret,
            code=auth_code,
            grant_type=GrantType.AUTHORIZATION_CODE,
        )
        try:
            token: GetUserTokenResponse = await client.get_user_token_async(get_user_token_request)
        except TeaException as err:
            if not UtilClient.empty(err.code) and not UtilClient.empty(err.message):
                raise DingDingException(f'Get access token error of code {err.code} and message {err.message}') from err
            raise

        return token.body

    async def _get_userid_by_unionid(self, unionid: UnionId, corp_id: CorpId) -> UserId:
        async with AsyncClient() as client:
            response = await client.post(
                url='https://oapi.dingtalk.com/topapi/user/getbyunionid',
                params={'access_token': await self.get_corp_token(corp_id)},
                json={"unionid": unionid},
            )
            if response.status_code != httpx.codes.OK or response.json().get('errcode', 0) != 0:
                raise Exception(  # pylint: disable=broad-exception-raised
                    f"根据 unionid 获取 userid 失败,状态码:{response.status_code},返回内容:{response.text}"
                )

            return response.json()['result']['userid']
