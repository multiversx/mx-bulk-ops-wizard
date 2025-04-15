import json
from pathlib import Path
from typing import Any, Optional

import pyotp
import requests
from multiversx_sdk import Address

from collector import errors


class CosignerRegistrationEntry:
    def __init__(self,
                 guardian: str,
                 scheme: str,
                 host: str,
                 issuer: str,
                 account: str,
                 algorithm: str,
                 digits: int,
                 period: int,
                 secret: str) -> None:
        self.guardian = guardian
        self.scheme = scheme
        self.host = host
        self.issuer = issuer
        self.account = account
        self.algorithm = algorithm
        self.digits = digits
        self.period = period
        self.secret = secret

    @classmethod
    def new_from_response_payload(cls, data: dict[str, Any]):
        guardian = data.get("guardian-address", "")

        otp = data.get("otp", {})
        scheme = otp.get("scheme", "")
        host = otp.get("host", "")
        issuer = otp.get("issuer", "")
        account = otp.get("account", "")
        algorithm = otp.get("algorithm", "")
        digits = int(otp.get("digits", 0))
        period = int(otp.get("period", 0))
        secret = otp.get("secret", "")

        return cls(
            guardian=guardian,
            scheme=scheme,
            host=host,
            issuer=issuer,
            account=account,
            algorithm=algorithm,
            digits=digits,
            period=period,
            secret=secret,
        )

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        guardian = data.get("guardian", "")
        scheme = data.get("scheme", "")
        host = data.get("host", "")
        issuer = data.get("issuer", "")
        account = data.get("account", "")
        algorithm = data.get("algorithm", "")
        digits = int(data.get("digits", 0))
        period = int(data.get("period", 0))
        secret = data.get("secret", "")

        return cls(
            guardian=guardian,
            scheme=scheme,
            host=host,
            issuer=issuer,
            account=account,
            algorithm=algorithm,
            digits=digits,
            period=period,
            secret=secret,
        )

    def to_dictionary(self) -> dict[str, Any]:
        return {
            "guardian": self.guardian,
            "scheme": self.scheme,
            "host": self.host,
            "issuer": self.issuer,
            "account": self.account,
            "algorithm": self.algorithm,
            "digits": self.digits,
            "period": self.period,
            "secret": self.secret,
        }


class CosignerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def register(self, native_auth_access_token: str, tag: str) -> CosignerRegistrationEntry:
        headers = {
            "Authorization": f"Bearer {native_auth_access_token}",
        }

        data = {
            "tag": tag
        }

        response = requests.post(f"{self.base_url}/guardian/register", headers=headers, json=data)
        payload = self._extract_response_payload(response)
        payload_typed = CosignerRegistrationEntry.new_from_response_payload(payload)
        return payload_typed

    def verify_code(self, native_auth_access_token: str, code: str, guardian: str):
        headers = {
            "Authorization": f"Bearer {native_auth_access_token}",
        }

        data = {
            "code": code,
            "guardian": guardian,
        }

        response = requests.post(f"{self.base_url}/guardian/verify-code", headers=headers, json=data)
        payload = self._extract_response_payload(response)
        print(payload)

    def _extract_response_payload(self, response: requests.Response) -> dict[str, Any]:
        respose_content = response.json()
        response_data = respose_content.get("data", {})
        response_error = respose_content.get("error", "")

        if response_error:
            raise errors.KnownError(response_error)

        return response_data


class OtpProvider:
    def __init__(self, registration_entries: list[CosignerRegistrationEntry]) -> None:
        self.registration_entries = registration_entries

    @classmethod
    def new_from_registration_file(cls, file: Path) -> "OtpProvider":
        file = file.expanduser().resolve()

        content = file.read_text()
        entries_raw: list[dict[str, Any]] = json.loads(content)
        entries = [CosignerRegistrationEntry.new_from_dictionary(entry) for entry in entries_raw]

        return OtpProvider(entries)

    def get_otp(self, address: Address) -> str:
        totp = pyotp.TOTP("...")
        code = totp.now()
        return code

    def ask_otp_multiple(self):
        pass
