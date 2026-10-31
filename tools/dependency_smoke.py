"""Exercise installed runtime wheels without source-tree imports or live servers."""

from importlib.resources import files
from tempfile import TemporaryDirectory

from cryptography.fernet import Fernet, InvalidToken

from jellyfin_msx.app import create_app
from jellyfin_msx.config import Settings
from jellyfin_msx.errors import PortalError
from jellyfin_msx.state import State


def main() -> None:
    # Synthetic random data only. Exercise persisted-token format and failure paths.
    cipher = Fernet(Fernet.generate_key())
    token = cipher.encrypt_at_time(b"synthetic dependency smoke", current_time=100)
    assert cipher.decrypt_at_time(token, ttl=10, current_time=105) == b"synthetic dependency smoke"
    for candidate, now in ((token, 111), (token[:-4] + b"xxxx", 105)):
        try:
            cipher.decrypt_at_time(candidate, ttl=10, current_time=now)
        except InvalidToken:
            pass
        else:
            raise AssertionError("Invalid Fernet token accepted")
    assert files("jellyfin_msx").joinpath("templates/pair.html").read_text(encoding="utf-8")
    assert files("jellyfin_msx").joinpath("templates/remember.html").read_text(encoding="utf-8")
    assert files("jellyfin_msx").joinpath("templates/remember.js").read_text(encoding="utf-8")
    # App construction is offline; normal HTTP/security routes remain in the mocked suite.
    settings = Settings(
        public_url="https://portal.invalid", jellyfin_url="https://jellyfin.invalid"
    )
    app = create_app(settings)
    assert any(route.path == "/healthz" for route in app.routes)
    with TemporaryDirectory() as directory:
        from dataclasses import replace
        from pathlib import Path

        path = Path(directory)
        path.chmod(0o700)
        durable = replace(
            settings,
            authorization_db=str(path / "authority.sqlite"),
            authorization_key=Fernet.generate_key().decode(),
        )
        first = State(durable)
        secret, device = first.pair()
        first.complete(device, "synthetic-user", "synthetic-upstream-token")
        renewal, expiry = first.remember(secret)
        restarted = State(durable)
        fresh, replacement, new_expiry = restarted.restore(renewal)
        assert restarted.get(fresh).user_id == "synthetic-user"
        assert replacement != renewal and expiry == new_expiry
        try:
            restarted.restore(renewal)
        except PortalError as exc:
            assert exc.status == 401
        else:
            raise AssertionError("Consumed renewal accepted")
    print("Installed wheel: template, app, Fernet, SQLite restart/rotation/replay denial passed")


if __name__ == "__main__":
    main()
