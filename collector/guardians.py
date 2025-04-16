import json
from pathlib import Path
from typing import Any, Optional

import pyotp
import requests

from collector import errors


class CosignerRegistrationEntry:
    def __init__(self,
                 address: str,
                 label: str,
                 guardian: str,
                 auth_metadata: dict[str, Any]) -> None:
        self.address = address
        self.label = label
        self.guardian = guardian
        self.auth_metadata = auth_metadata

    @classmethod
    def new_from_response_payload(cls, address: str, label: str, data: dict[str, Any]):
        guardian = data.get("guardian-address", "")
        otp = data.get("otp", {})

        return cls(
            address=address,
            label=label,
            guardian=guardian,
            auth_metadata=otp
        )

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        address = data.get("address", "")
        label = data.get("label", "")
        guardian = data.get("guardian", "")
        auth_metadata = data.get("authMetadata", {})

        return cls(
            address=address,
            label=label,
            guardian=guardian,
            auth_metadata=auth_metadata,
        )

    def to_dictionary(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "label": self.label,
            "guardian": self.guardian,
            "authMetadata": self.auth_metadata,
        }

    def get_secret(self) -> str:
        return self.auth_metadata.get("secret", "")


class CosignerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def register(self, address: str, label: str, native_auth_access_token: str, tag: str) -> CosignerRegistrationEntry:
        headers = {
            "Authorization": f"Bearer {native_auth_access_token}",
        }

        data = {
            "tag": tag
        }

        response = requests.post(f"{self.base_url}/guardian/register", headers=headers, json=data)
        payload = self._extract_response_payload(response)
        payload_typed = CosignerRegistrationEntry.new_from_response_payload(address, label, payload)
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


class AuthApp:
    def __init__(self, registration_entries: list[CosignerRegistrationEntry]) -> None:
        self.registration_entries_by_address: dict[str, CosignerRegistrationEntry] = {entry.address: entry for entry in registration_entries}
        self.codes_from_outside_by_address: dict[str, str] = {}

    @classmethod
    def new_from_registration_file(cls, file: Path) -> "AuthApp":
        file = file.expanduser().resolve()

        content = file.read_text()
        entries_raw: list[dict[str, Any]] = json.loads(content)
        entries = [CosignerRegistrationEntry.new_from_dictionary(entry) for entry in entries_raw]

        return AuthApp(entries)

    def learn_registration_entry(self, entry: CosignerRegistrationEntry):
        self.registration_entries_by_address[entry.address] = entry

    def get_code(self, address: str) -> str:
        entry = self.registration_entries_by_address.get(address)
        if entry is not None:
            secret = entry.get_secret()
            return self.get_code_given_secret(secret)

        while address not in self.codes_from_outside_by_address:
            self.ask_for_codes_from_outside()

        return self.codes_from_outside_by_address[address]

    def get_code_given_secret(self, secret: str) -> str:
        totp = pyotp.TOTP(secret)
        code = totp.now()
        return code

    def ask_for_codes_from_outside(self):
        self.codes_from_outside_by_address = {}

    def export_to_registration_file(self, file: Path):
        entries = [entry for entry in self.registration_entries_by_address.values()]
        entries_json = json.dumps([entry.to_dictionary() for entry in entries], indent=4)
        file.write_text(entries_json)
