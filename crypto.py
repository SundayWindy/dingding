#  code copy from https://github.com/shuizhengqi1/DingCrypto/blob/master/DingCrypto.py

# 依赖Crypto类库
# sudo pip3 install pycrypto  python3 安装Crypto
# API说明
# get_encrypted_map 生成回调处理成功后success加密后返回给钉钉的json数据
# decrypt  用于从钉钉接收到回调请求后

"""
token          钉钉开放平台上，开发者设置的token
encodingAesKey 钉钉开放台上，开发者设置的EncodingAESKey
corpId         企业自建应用-事件订阅, 使用appKey
               企业自建应用-注册回调地址, 使用corpId
               第三方企业应用, 使用suiteKey
"""

import base64
import binascii
import hashlib
import io
import string
import struct
import time
from random import choice
from typing import Any

# pylint: disable=no-name-in-module
# pylint: disable=import-error
from Crypto.Cipher import AES


class DingCallbackCrypto3:
    def __init__(self, token: str, encoding_aes_key: str, key: str):
        # https://open-dev.dingtalk.com/fe/app#/appMgr/provider/h5/119556/17
        self.encoding_aes_key = encoding_aes_key
        self.key = key
        self.token = token
        self.aes_key = base64.b64decode(self.encoding_aes_key + '=')

    # 生成回调处理完成后的success加密数据
    def get_encrypted_map(self, content):
        encrypt_content = self.encrypt(content)
        time_stamp = str(int(time.time()))
        nonce = self.generate_random_key(16)
        sign = self.generate_signature(nonce, time_stamp, self.token, encrypt_content)
        return {'msg_signature': sign, 'encrypt': encrypt_content, 'timeStamp': time_stamp, 'nonce': nonce}

    # 解密钉钉发送的数据
    def get_decrypt_msg(self, msg_signature: str, time_stamp: str, nonce: str, content: str) -> str:
        """
        解密
        """
        sign = self.generate_signature(nonce, time_stamp, self.token, content)
        # print(sign, msg_signature)
        if msg_signature != sign:
            raise ValueError('signature check error')

        content = base64.decodebytes(content.encode('UTF-8'))  # 钉钉返回的消息体

        iv = self.aes_key[:16]  # 初始向量
        aes_decode = AES.new(self.aes_key, AES.MODE_CBC, iv)

        decode_res = aes_decode.decrypt(content)
        # pad = int(binascii.hexlify(decode_res[-1]),16)
        pad = int(decode_res[-1])
        if pad > 32:
            raise ValueError('Input is not padded or padding is corrupt')
        decode_res = decode_res[:-pad]
        l = struct.unpack('!i', decode_res[16:20])[0]
        # 获取去除初始向量，四位msg长度以及尾部corpid
        # nl = len(decode_res)

        if decode_res[(20 + l) :].decode() != self.key:
            raise ValueError('corpId 校验错误')
        return decode_res[20 : (20 + l)].decode()

    def encrypt(self, content):
        """
        加密
        :param content:
        :return:
        """
        msg_len = self.length(content)
        content = ''.join([self.generate_random_key(16), msg_len.decode(), content, self.key])
        content_encode = self.pks7encode(content)
        iv = self.aes_key[:16]
        aes_encode = AES.new(self.aes_key, AES.MODE_CBC, iv)
        aes_encrypt = aes_encode.encrypt(content_encode.encode('UTF-8'))
        return base64.encodebytes(aes_encrypt).decode('UTF-8')

    # 生成回调返回使用的签名值
    @classmethod
    def generate_signature(cls, nonce: str, timestamp: str, token: str, msg_encrypt: str) -> str:
        # print(type(nonce), type(timestamp), type(token), type(msg_encrypt))
        v = msg_encrypt
        sign_list = ''.join(sorted([nonce, timestamp, token, v]))
        return hashlib.sha1(sign_list.encode()).hexdigest()

    @classmethod
    def length(cls, content: str) -> bytes:
        """
        将msg_len转为符合要求的四位字节长度
        """
        l = len(content)
        return struct.pack('>l', l)

    @classmethod
    def pks7encode(cls, content: str) -> str:
        """
        安装 PKCS#7 标准填充字符串
        """
        l = len(content)
        output = io.StringIO()
        val = 32 - (l % 32)
        for _ in range(val):
            output.write('%02x' % val)  # pylint: disable=consider-using-f-string
        # print "pks7encode",content,"pks7encode", val, "pks7encode", output.getvalue()
        return content + binascii.unhexlify(output.getvalue()).decode()

    @classmethod
    def pks7decode(cls, content: Any) -> str:
        nl = len(content)
        val = int(binascii.hexlify(content[-1]), 16)
        if val > 32:
            raise ValueError('Input is not padded or padding is corrupt')

        l = nl - val
        return content[:l]

    @classmethod
    def generate_random_key(
        cls,
        size,
        chars=string.ascii_letters + string.ascii_lowercase + string.ascii_uppercase + string.digits,
    ):
        """
        生成加密所需要的随机字符串
        """
        return ''.join(choice(chars) for i in range(size))
