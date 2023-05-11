from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from typing import Optional


@dataclass
class AccessToken:
    value: str
    expires_in: int

    expires_at: Optional[datetime] = field(init=False)

    def __post_init__(self):
        self.expires_at = datetime.now() + timedelta(seconds=self.expires_in)

    def is_expired(self) -> bool:
        return self.expires_at < datetime.now()
