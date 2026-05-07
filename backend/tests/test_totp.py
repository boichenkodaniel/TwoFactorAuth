import pytest
import pyotp
from app.services.totp_service import TOTPService


def test_generate_secret():
    secret = TOTPService.generate_secret()

    assert secret is not None
    assert isinstance(secret, str)
    assert len(secret) > 0


def test_generate_totp():
    secret = TOTPService.generate_secret()
    code = TOTPService.generate_totp(secret)

    assert code is not None
    assert isinstance(code, str)
    assert len(code) == 6
    assert code.isdigit()


def test_verify_totp_valid():
    secret = TOTPService.generate_secret()
    code = TOTPService.generate_totp(secret)

    is_valid = TOTPService.verify_totp(secret, code)

    assert is_valid is True


def test_verify_totp_invalid():
    secret = TOTPService.generate_secret()

    is_valid = TOTPService.verify_totp(secret, "000000")

    assert is_valid is False


def test_verify_totp_expired():
    secret = TOTPService.generate_secret()
    code = TOTPService.generate_totp(secret)

    totp = pyotp.TOTP(secret)
    previous_code = totp.at(int(totp.now()) - 60)

    is_valid = TOTPService.verify_totp(secret, previous_code)

    assert is_valid is False
