import json
from enum import Enum
from pathlib import Path
from typing import Any

from collector.errors import BadConfigurationError


class WalletsConfiguration:
    def __init__(self, entries: list["WalletEntry"]) -> None:
        self.entries = entries

    @classmethod
    def new_from_file(cls, file: Path) -> "WalletsConfiguration":
        file = file.expanduser().resolve()

        content = file.read_text()
        entries_raw: list[dict[str, Any]] = json.loads(content)
        entries: list[WalletEntry] = []

        for entry_raw in entries_raw:
            kind = WalletKind(entry_raw.get("kind"))

            if kind == WalletKind.Mnemonic:
                entries.append(MnemonicWalletEntry.new_from_dictionary(entry_raw))
            elif kind == WalletKind.Keystore:
                entries.append(KeystoreWalletEntry.new_from_dictionary(entry_raw))
            elif kind == WalletKind.Keystores:
                entries.append(KeystoresWalletEntry.new_from_dictionary(entry_raw))
            elif kind == WalletKind.Ledger:
                entries.append(LedgerWalletEntry.new_from_dictionary(entry_raw))
            else:
                raise BadConfigurationError(f"unknown wallet kind: {kind}")

        return WalletsConfiguration(entries)


class WalletEntry:
    def __init__(self, kind: "WalletKind") -> None:
        self.kind = kind


class WalletKind(str, Enum):
    Mnemonic = "mnemonic"
    Keystore = "keystore"
    Keystores = "keystores"
    Ledger = "ledger"


class MnemonicWalletEntry(WalletEntry):
    def __init__(self,
                 mnemonic: str,
                 mnemonic_file: str,
                 address_indices: list[int]) -> None:
        super().__init__(WalletKind.Mnemonic)

        self.mnemonic = mnemonic
        self.mnemonic_file = mnemonic_file
        self.address_indices = address_indices

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.Mnemonic

        mnemonic = data.get("mnemonic") or ""
        mnemonic_file = data.get("mnemonicFile") or ""
        address_indices = data.get("addressIndices") or []

        return cls(
            mnemonic=mnemonic,
            mnemonic_file=mnemonic_file,
            address_indices=address_indices
        )


class KeystoreWalletEntry(WalletEntry):
    def __init__(self,
                 file: str,
                 password: str,
                 password_file: str,
                 address_indices: list[int]) -> None:
        super().__init__(WalletKind.Keystore)

        self.file = file
        self.password = password
        self.password_file = password_file
        self.address_indices = address_indices

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.Keystore

        file = data.get("file") or ""
        password = data.get("password") or ""
        password_file = data.get("passwordFile") or ""
        address_indices = data.get("addressIndices") or []

        return cls(
            file=file,
            password=password,
            password_file=password_file,
            address_indices=address_indices
        )


class KeystoresWalletEntry(WalletEntry):
    def __init__(self,
                 folder: str,
                 unique_password: str,
                 unique_password_file: str) -> None:
        super().__init__(WalletKind.Keystores)

        self.folder = folder
        self.unique_password = unique_password
        self.unique_password_file = unique_password_file

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.Keystores

        folder = data.get("folder") or ""
        unique_password = data.get("uniquePassword") or ""
        unique_password_file = data.get("uniquePasswordFile") or ""

        return cls(
            folder=folder,
            unique_password=unique_password,
            unique_password_file=unique_password_file
        )


class LedgerWalletEntry(WalletEntry):
    def __init__(self,
                 address_indices: list[int]) -> None:
        super().__init__(WalletKind.Ledger)

        self.address_indices = address_indices

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.Ledger

        address_indices = data.get("addressIndices") or []

        return cls(
            address_indices=address_indices
        )
