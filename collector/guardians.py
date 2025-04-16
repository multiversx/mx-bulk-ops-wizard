import json
import sys
from pathlib import Path
from typing import Any

import pyotp
import requests
from rich import print

from collector import errors, ux


class GuardianData:
    def __init__(self,
                 is_guarded: bool,
                 active_epoch: int,
                 active_guardian: str,
                 active_service: str,
                 pending_epoch: int,
                 pending_guardian: str,
                 pending_service: str) -> None:
        self.is_guarded = is_guarded
        self.active_epoch = active_epoch
        self.active_guardian = active_guardian
        self.active_service = active_service
        self.pending_epoch = pending_epoch
        self.pending_guardian = pending_guardian
        self.pending_service = pending_service

    @classmethod
    def new_from_response_payload(cls, data: dict[str, Any]):
        is_guarded = data.get("guarded", False)

        active_data = data.get("activeGuardian", {})
        active_epoch = active_data.get("activationEpoch", 0)
        active_guardian = active_data.get("address", "")
        active_service = active_data.get("serviceUID", "")

        pending_data = data.get("pendingGuardian", {})
        pending_epoch = pending_data.get("activationEpoch", 0)
        pending_guardian = pending_data.get("address", "")
        pending_service = pending_data.get("serviceUID", "")

        return cls(
            is_guarded=is_guarded,
            active_epoch=active_epoch,
            active_guardian=active_guardian,
            active_service=active_service,
            pending_epoch=pending_epoch,
            pending_guardian=pending_guardian,
            pending_service=pending_service,
        )


class CosignerRegistrationEntry:
    def __init__(self,
                 address: str,
                 wallet_name: str,
                 guardian: str,
                 auth_metadata: dict[str, Any]) -> None:
        self.address = address
        self.wallet_name = wallet_name
        self.guardian = guardian
        self.auth_metadata = auth_metadata

    @classmethod
    def new_from_response_payload(cls, address: str, wallet_name: str, data: dict[str, Any]):
        guardian = data.get("guardian-address", "")
        otp = data.get("otp", {})

        return cls(
            address=address,
            wallet_name=wallet_name,
            guardian=guardian,
            auth_metadata=otp
        )

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        address = data.get("address", "")
        wallet_name = data.get("walletName", "")
        guardian = data.get("guardian", "")
        auth_metadata = data.get("authMetadata", {})

        return cls(
            address=address,
            wallet_name=wallet_name,
            guardian=guardian,
            auth_metadata=auth_metadata,
        )

    def to_dictionary(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "walletName": self.wallet_name,
            "guardian": self.guardian,
            "authMetadata": self.auth_metadata,
        }

    def get_secret(self) -> str:
        return self.auth_metadata.get("secret", "")


class CosignerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def register(self, native_auth_access_token: str, address: str, wallet_name: str) -> CosignerRegistrationEntry:
        headers = {
            "Authorization": f"Bearer {native_auth_access_token}",
        }

        data = {
            "tag": wallet_name
        }

        response = requests.post(f"{self.base_url}/guardian/register", headers=headers, json=data)
        payload = self._extract_response_payload(response)
        payload_typed = CosignerRegistrationEntry.new_from_response_payload(address, wallet_name, payload)
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
        _ = self._extract_response_payload(response)

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

        print(f"Missing registration entry for [yellow]{address}[/yellow].")

        while address not in self.codes_from_outside_by_address:
            print(f"Missing code for [yellow]{address}[/yellow].")
            self.ask_for_codes_from_outside()

        return self.codes_from_outside_by_address[address]

    def get_code_given_secret(self, secret: str) -> str:
        totp = pyotp.TOTP(secret)
        code = totp.now()
        return code

    def ask_for_codes_from_outside(self):
        self.codes_from_outside_by_address = {}

        print("Please provide authentication codes in the following format (example):")
        print("erd1qyu5wthldzr8wx5c9ucg8kjagg0jfs53s8nr3zpz3hypefsdd8ssycr6th 123456")
        print("erd1k2s324ww2g0yj38qn2ch2jwctdy8mnfxep94q9arncc6xecg3xaq6mjse8 654321")
        print()
        print("Insert text below. Press 'Ctrl-D' (Linux / MacOS) or 'Ctrl-Z' (Windows) when done.")

        input_text = sys.stdin.read().strip()
        input_lines = input_text.splitlines()

        for line in input_lines:
            parts = line.split()

            if len(parts) != 2:
                ux.show_warning(f"Bad line: {line}")
                continue

            address, code = parts
            self.codes_from_outside_by_address[address] = code

    def export_to_registration_file(self, file: Path):
        entries = [entry for entry in self.registration_entries_by_address.values()]
        entries_json = json.dumps([entry.to_dictionary() for entry in entries], indent=4)
        file.write_text(entries_json)
