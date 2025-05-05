import json
from pathlib import Path
from typing import Any, Optional

import pyotp
import requests
from multiversx_sdk import Transaction
from rich import print
from rich.prompt import Prompt

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


class AuthRegistrationEntry:
    def __init__(self,
                 context: dict[str, Any],
                 issuer: str,
                 label: str,
                 algorithm: str,
                 digits: int,
                 interval: int,
                 secret: str) -> None:
        self.context = context
        self.issuer = issuer
        self.label = label
        self.algorithm = algorithm
        self.digits = digits
        self.interval = interval
        self.secret = secret

    def get_address(self) -> str:
        if "address" not in self.context:
            raise errors.ProgrammingError("'address' not found in registration context")

        return self.context["address"]

    def get_guardian(self) -> str:
        if "guardian" not in self.context:
            raise errors.ProgrammingError("'guardian' not found in registration context")

        return self.context["guardian"]

    @classmethod
    def new_from_response_payload(cls, address: str, wallet_name: str, data: dict[str, Any]):
        guardian = data.get("guardian-address", "")

        context = {
            "address": address,
            "walletName": wallet_name,
            "guardian": guardian,
        }

        otp = data.get("otp", {})
        issuer = otp.get("issuer", "")
        algorithm = otp.get("algorithm", "").lower()
        digits = int(otp.get("digits", 0))
        interval = int(otp.get("period", 0))
        secret = otp.get("secret", "")

        return cls(
            context=context,
            issuer=issuer,
            label=wallet_name,
            algorithm=algorithm,
            digits=digits,
            interval=interval,
            secret=secret
        )

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        context = data.get("context", {})

        # Handle synonyms, on a best-effort basis.
        issuer = data.get("issuer", "")
        label = (data.get("account", "")
                 or data.get("name", "")
                 or data.get("label", "")
                 or data.get("tag", ""))
        algorithm = data.get("algorithm", "")
        digits = data.get("digits", 0)
        interval = (data.get("interval", 0)
                    or data.get("period", 0))
        secret = data.get("secret", "")

        return cls(
            context=context,
            issuer=issuer,
            label=label,
            algorithm=algorithm,
            digits=digits,
            interval=interval,
            secret=secret,
        )

    def to_dictionary(self) -> dict[str, Any]:
        return {
            "context": self.context,
            "issuer": self.issuer,
            "label": self.label,
            "algorithm": self.algorithm,
            "digits": self.digits,
            "interval": self.interval,
            "secret": self.secret,
        }


class CosignerClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def register(self, native_auth_access_token: str, address: str, wallet_name: str) -> AuthRegistrationEntry:
        headers = {
            "Authorization": f"Bearer {native_auth_access_token}",
        }

        data = {
            "tag": wallet_name
        }

        response = requests.post(f"{self.base_url}/guardian/register", headers=headers, json=data)
        payload = self._extract_response_payload(response)
        payload_typed = AuthRegistrationEntry.new_from_response_payload(address, wallet_name, payload)
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

    def sign_multiple_transactions(self, code: str, transactions: list[Transaction]):
        print(f"sign_multiple_transactions, code = {code}, len(transactions) = {len(transactions)}")

        data = {
            "code": code,
            "transactions": [transaction.to_dictionary() for transaction in transactions],
        }

        response = requests.post(f"{self.base_url}/guardian/sign-multiple-transactions", json=data)
        payload = self._extract_response_payload(response)
        signed_transactions = payload.get("transactions", [])

        # We patch the transactions signatures inline (we don't blindly accept the response).
        # We expect transaction order to not change (though, we do check).
        for index, transaction in enumerate(transactions):
            sender_signature = bytes.fromhex(signed_transactions[index].get("signature", ""))
            guardian_signature = bytes.fromhex(signed_transactions[index].get("guardianSignature", ""))

            assert transaction.signature == sender_signature, "unexpected cosigner response"
            assert len(guardian_signature) > 0, "unexpected cosigner response"
            assert (transaction.guardian.to_bech32() if transaction.guardian else "") == signed_transactions[index].get("guardian")

            transaction.guardian_signature = guardian_signature

    def _extract_response_payload(self, response: requests.Response) -> dict[str, Any]:
        respose_content = response.json()
        response_data = respose_content.get("data", {})
        response_error = respose_content.get("error", "")

        if response_error:
            raise errors.KnownError(response_error)

        return response_data


class AuthApp:
    def __init__(self, registration_entries: list[AuthRegistrationEntry]) -> None:
        self.registration_entries_by_address: dict[str, AuthRegistrationEntry] = {entry.get_address(): entry for entry in registration_entries}

    @classmethod
    def new_from_registration_file(cls, file: Path) -> "AuthApp":
        file = file.expanduser().resolve()

        content = file.read_text()
        entries_raw: list[dict[str, Any]] = json.loads(content)
        entries = [AuthRegistrationEntry.new_from_dictionary(entry) for entry in entries_raw]

        return AuthApp(entries)

    def get_registration_entry(self, address: str) -> Optional[AuthRegistrationEntry]:
        return self.registration_entries_by_address.get(address)

    def learn_registration_entry(self, entry: AuthRegistrationEntry):
        self.registration_entries_by_address[entry.get_address()] = entry

    def get_code(self, address: str) -> str:
        entry = self.registration_entries_by_address.get(address)
        if entry is not None:
            secret = entry.secret
            return self.get_code_given_secret(secret)

        print(f"Missing registration entry for [yellow]{address}[/yellow].")
        code = Prompt.ask(f"Enter code for [yellow]{address}[/yellow]")
        return code

    def get_code_given_secret(self, secret: str) -> str:
        totp = pyotp.TOTP(secret)
        code = totp.now()
        return code

    def export_to_registration_file(self, file: Path):
        entries = self.get_all_entries()
        entries_json = json.dumps([entry.to_dictionary() for entry in entries], indent=4)
        file.write_text(entries_json)

    def get_all_entries(self):
        entries = [entry for entry in self.registration_entries_by_address.values()]
        return entries
