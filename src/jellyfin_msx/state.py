import hashlib
import re
import secrets
import time
from dataclasses import dataclass, field

from .authorization import AuthorizationStore
from .config import Settings
from .errors import PortalError


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass
class Device:
    expires: float
    device_id: str = field(default_factory=lambda: secrets.token_hex(16))
    code: str | None = None
    user_id: str | None = None
    token: str | None = field(default=None, repr=False)
    claiming: bool = False
    authorization_generation: int | None = None
    diagnostics: list[dict] = field(default_factory=list)


class State:
    """Single-event-loop state. No await between checking and claiming a pairing."""

    def __init__(self, settings: Settings, clock=time.monotonic, wall_clock=time.time):
        self.settings = settings
        self.clock = clock
        self.devices: dict[str, Device] = {}
        self.rates: dict[str, tuple[float, int]] = {}
        self.authorizations = (
            AuthorizationStore(settings, wall_clock) if settings.authorization_db else None
        )

    def prune(self):
        now = self.clock()
        self.devices = {k: v for k, v in self.devices.items() if v.expires > now}
        self.rates = {k: v for k, v in self.rates.items() if v[0] > now}

    def limit(self, key: str, maximum: int, seconds: int = 60):
        self.prune()
        expiry, count = self.rates.get(key, (self.clock() + seconds, 0))
        if count >= maximum or (key not in self.rates and len(self.rates) >= 1024):
            raise PortalError(429, "Too many attempts. Wait a minute and retry.")
        self.rates[key] = expiry, count + 1

    def pair(self) -> tuple[str, Device]:
        self.prune()
        if len(self.devices) >= self.settings.max_states:
            raise PortalError(503, "Pairing capacity reached. Retry later.")
        secret = secrets.token_urlsafe(32)
        codes = {v.code for v in self.devices.values() if v.code}
        code = f"{secrets.randbelow(100_000_000):08d}"
        while code in codes:
            code = f"{secrets.randbelow(100_000_000):08d}"
        device = Device(self.clock() + self.settings.pairing_ttl, code=code)
        self.devices[digest(secret)] = device
        return secret, device

    def get(self, secret: str, authenticated=True) -> Device:
        self.prune()
        device = self.devices.get(digest(secret))
        if device is None or (authenticated and not device.token):
            raise PortalError(401, "Session missing or expired. Reopen the MSX start page to pair.")
        if device.authorization_generation is not None:
            self.authorizations.validate(device)
        return device

    def claim(self, code: str) -> Device:
        self.prune()
        if not re.fullmatch(r"[0-9]{8}", code):
            raise PortalError(400, "Pairing failed. Check the current TV code and credentials.")
        for device in self.devices.values():
            if device.code and secrets.compare_digest(device.code, code) and not device.claiming:
                device.claiming = True
                return device
        raise PortalError(
            400,
            "TV code is invalid, expired or already used. "
            "Select Create new code in Media Station X and try again.",
        )

    def complete(self, device: Device, user: str, token: str):
        if device.expires <= self.clock() or not any(v is device for v in self.devices.values()):
            raise PortalError(400, "Pairing expired. Create a new code on the TV.")
        device.user_id, device.token, device.code = user, token, None
        device.expires = self.clock() + self.settings.session_ttl

    def remove(self, secret: str):
        device = self.devices.get(digest(secret))
        if device and device.authorization_generation is not None:
            self.authorizations.revoke(device.device_id)
        self.devices.pop(digest(secret), None)

    def remember(self, secret):
        if not self.authorizations:
            raise PortalError(404, "Durable authorization is disabled.")
        device = self.get(secret)
        renewal, expires = self.authorizations.enroll(device)
        device.authorization_generation = 0
        return renewal, expires

    def restore(self, renewal):
        if not self.authorizations:
            raise PortalError(404, "Durable authorization is disabled.")
        self.prune()
        if len(self.devices) >= self.settings.max_states:
            raise PortalError(503, "Session capacity reached. Retry later.")
        data, generation, replacement = self.authorizations.rotate(renewal)
        # A successful rotation invalidates older sessions, even in another process.
        self.devices = {k: v for k, v in self.devices.items() if v.device_id != data["id"]}
        secret = secrets.token_urlsafe(32)
        device = Device(
            self.clock()
            + min(self.settings.session_ttl, data["expires"] - self.authorizations.clock()),
            device_id=data["id"],
            user_id=data["user"],
            token=data["token"],
            authorization_generation=generation,
        )
        self.devices[digest(secret)] = device
        return secret, replacement, data["expires"]

    def record(self, device: Device, event: dict):
        device.diagnostics.append(event)
        del device.diagnostics[:-20]
