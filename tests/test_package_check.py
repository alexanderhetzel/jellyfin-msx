import zipfile

import pytest

from tools import package_check


def test_allowlist_rejects_unexpected_or_modified_bytes():
    package_check.check_files({"module.py": b"reviewed"}, {"module.py": b"reviewed"})
    with pytest.raises(ValueError, match="allowlist"):
        package_check.check_files({"private.sqlite": b"state"}, {})
    with pytest.raises(ValueError, match="differ"):
        package_check.check_files({"module.py": b"changed"}, {"module.py": b"reviewed"})
    with pytest.raises(ValueError, match="canary"):
        package_check.check_files(
            {"module.py": package_check.CANARY}, {"module.py": package_check.CANARY}
        )


def test_canary_never_overwrites_existing_files(tmp_path):
    first = tmp_path / package_check.CANARY_PATHS[0]
    first.write_text("operator")
    with pytest.raises(ValueError, match="already exists"):
        package_check.seed(tmp_path)
    package_check.clean(tmp_path)
    assert first.read_text() == "operator"
    assert not (tmp_path / package_check.CANARY_PATHS[1]).exists()


def test_wheel_rejects_duplicate_members(tmp_path):
    wheel = tmp_path / "duplicate.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("module.py", b"original")
        with pytest.warns(UserWarning, match="Duplicate"):
            archive.writestr("module.py", b"replacement")
    with pytest.raises(ValueError, match="Duplicate"):
        package_check.wheel_files(wheel, tmp_path)
