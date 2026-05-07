import pyotp


class TOTPService:


    @staticmethod
    def generate_secret() -> str:
        return pyotp.random_base32()

    @staticmethod
    def generate_totp(secret: str) -> str:
        totp = pyotp.TOTP(secret)
        return totp.now()

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        totp = pyotp.TOTP(secret)
        return totp.verify(code)

    @classmethod
    def build_provisioning_uri(cls, secret: str, account_name: str) -> str:
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=account_name)
