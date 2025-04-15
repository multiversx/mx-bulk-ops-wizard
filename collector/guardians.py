from typing import Any

import requests

from collector import errors


class CosignerRegisterResponse:
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
    def new_from_dictionary(cls, data: dict[str, Any]):
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


class CosignerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def register(self, native_auth_access_token: str, tag: str) -> CosignerRegisterResponse:
        headers = {
            "Authorization": f"Bearer {native_auth_access_token}",
        }

        data = {
            "tag": tag
        }

        response = requests.post(f"{self.base_url}/guardian/register", headers=headers, json=data)
        payload = self._extract_response_payload(response)
        payload_typed = CosignerRegisterResponse.new_from_dictionary(payload)
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
