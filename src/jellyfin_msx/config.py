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
    enable_subtitle_resources: bool = False
    original_delivery: str = "legacy"
    original_server_contract: str | None = None
    original_server_version: str | None = None
    authorization_db: str | None = None
    authorization_key: str | None = field(default=None, repr=False)
    authorization_ttl: int = 30 * 86400
    remember_devices: bool = False

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
        if self.original_delivery not in {"legacy", "authenticated-file-candidate"}:
            raise ValueError("Unknown original delivery mode")
        if self.original_delivery == "authenticated-file-candidate":
            if (
                self.original_server_contract != "stock-static-private-origin-v1"
                or self.original_server_version
                not in {"12.0.0", "12.1.0", "12.2.0", "12.3.0", "12.4.0"}
                or self.allow_transcoding
                or not all(
                    value.startswith("https://") for value in (self.public_url, self.jellyfin_url)
                )
            ):
                raise ValueError(
                    "Candidate requires declared stock/static private-origin contract, "
                    "supported exact release, HTTPS and no conversion"
                )
            portal_host = urlsplit(self.public_url).hostname.rstrip(".")
            if portal_host in {
                "github.com",
                "raw.githubusercontent.com",
                "raw.githack.com",
                "rawcdn.githack.com",
            } or portal_host.endswith((".githack.com", ".githubusercontent.com")):
                raise ValueError("Candidate requires an operator-controlled private portal origin")
        if self.enable_subtitle_resources and not all(
            value.startswith("https://") for value in (self.public_url, self.jellyfin_url)
        ):
            raise ValueError("Subtitle resources require HTTPS portal and Jellyfin origins")
        if bool(self.authorization_db) != bool(self.authorization_key):
            raise ValueError("Authorization database and external key must be configured together")
        if not 1 <= self.authorization_ttl <= 90 * 86400:
            raise ValueError("Authorization lifetime must be between 1 second and 90 days")
        if self.authorization_db and (
            not Path(self.authorization_db).is_absolute()
            or not self.public_url.startswith("https://")
        ):
            raise ValueError("Durable authorization requires an absolute database path and HTTPS")
        if self.remember_devices and not self.authorization_db:
            raise ValueError("Remembered devices require configured durable authorization")

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
            enable_subtitle_resources=os.getenv("MSX_ENABLE_SUBTITLE_RESOURCES", "false").lower()
            == "true",
            original_delivery=os.getenv("MSX_ORIGINAL_DELIVERY", "legacy"),
            original_server_contract=os.getenv("MSX_ORIGINAL_SERVER_CONTRACT") or None,
            original_server_version=os.getenv("MSX_ORIGINAL_SERVER_VERSION") or None,
            authorization_db=os.getenv("MSX_AUTHORIZATION_DB") or None,
            authorization_key=os.getenv("MSX_AUTHORIZATION_KEY") or None,
            authorization_ttl=int(os.getenv("MSX_AUTHORIZATION_TTL", str(30 * 86400))),
            remember_devices=os.getenv("MSX_REMEMBER_DEVICES", "false").lower() == "true",
        )
