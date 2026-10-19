import hashlib
import json

import pytest

from core import admin_auth


def test_admin_account_is_created_without_storing_plaintext_password(
    tmp_path, monkeypatch
):
    account_path = tmp_path / "data" / "admin_account.json"
    monkeypatch.setattr(admin_auth, "_ACCOUNT_FILE", account_path)
    password = "test-only-password-123"

    admin_auth._save_account("MSU", password)
    account = json.loads(account_path.read_text(encoding="utf-8"))

    assert account["username"] == "MSU"
    assert account["password_hash"] != password
    assert password not in account_path.read_text(encoding="utf-8")
    assert account["password_hash"] == hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(account["salt"]),
        account["iterations"],
    ).hex()


def test_admin_account_setup_does_not_overwrite_existing_account(
    tmp_path, monkeypatch
):
    account_path = tmp_path / "data" / "admin_account.json"
    monkeypatch.setattr(admin_auth, "_ACCOUNT_FILE", account_path)
    admin_auth._save_account("MSU", "test-only-password-123")

    with pytest.raises(FileExistsError):
        admin_auth._save_account("attacker", "AnotherPassword@123")

    assert admin_auth._read_account()["username"] == "MSU"
