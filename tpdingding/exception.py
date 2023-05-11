import httpx


class DingDingException(Exception):
    def __init__(
        self,
        message: str,
        errcode: int = httpx.codes.INTERNAL_SERVER_ERROR,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.errcode = errcode
