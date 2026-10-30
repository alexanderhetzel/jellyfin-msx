import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    public_url: str
    jellyfin_url: str
    allow_http: bool = False
    session_ttl: int = 28800
    pairing_ttl: int = 300
    max_states: int = 256
    max_bitrate: int | None = None
    allow_transcoding: bool = False
    authorization_db: str | None = None
    authorization_key: str | None = field(default=None, repr=False)
    authorization_ttl: int = 30 * 86400

    def __post_init__(self):
        for name in ("public_url", "jellyfin_url"):
            value = getattr(self, name).rstrip("/")
            parts = urlsplit(value)
            if parts.port is not None and not 1 <= parts.port <= 65535:
                raise ValueError(f"Invalid port in {name}")
            if (
                parts.scheme not in ({"https", "http"} if self.allow_http else {"https"})
                or not parts.hostname
                or parts.username
                or parts.password
                or parts.query
                or parts.fragment
                or any(c in value for c in ('"', "<", ">", "{", "}", "|", "\\", " "))
                or any(ord(c) < 32 for c in value)
                or any(p in {".", ".."} for p in parts.path.split("/"))
            ):
                raise ValueError(f"Invalid {name}; use a credential-free HTTPS URL")
            if name == "public_url" and parts.path:
                raise ValueError("public_url must be an origin without a path")
            object.__setattr__(self, name, value)
        if self.max_bitrate is not None and (
            isinstance(self.max_bitrate, bool)
            or not isinstance(self.max_bitrate, int)
            or not 1 <= self.max_bitrate <= 1_000_000_000
        ):
            raise ValueError(
                "max_bitrate must be unset or a positive operator budget up to 1 Gbit/s"
            )
        if min(self.session_ttl, self.pairing_ttl, self.max_states) <= 0:
            raise ValueError("State limits must be positive")
        if bool(self.authorization_db) != bool(self.authorization_key):
            raise ValueError("Authorization database and external key must be configured together")
        if not 1 <= self.authorization_ttl <= 90 * 86400:
            raise ValueError("Authorization lifetime must be between 1 second and 90 days")
        if self.authorization_db and (
            not Path(self.authorization_db).is_absolute()
            or not self.public_url.startswith("https://")
        ):
            raise ValueError("Durable authorization requires an absolute database path and HTTPS")

    @classmethod
    def from_env(cls):
        return cls(
            public_url=os.environ["MSX_PUBLIC_URL"],
            jellyfin_url=os.environ["JELLYFIN_URL"],
            allow_http=os.getenv("MSX_ALLOW_HTTP", "false").lower() == "true",
            max_bitrate=int(os.environ["MSX_MAX_BITRATE"])
            if os.getenv("MSX_MAX_BITRATE", "").strip()
            else None,
            allow_transcoding=os.getenv("MSX_ALLOW_TRANSCODING", "false").lower() == "true",
            authorization_db=os.getenv("MSX_AUTHORIZATION_DB") or None,
            authorization_key=os.getenv("MSX_AUTHORIZATION_KEY") or None,
            authorization_ttl=int(os.getenv("MSX_AUTHORIZATION_TTL", str(30 * 86400))),
        )
