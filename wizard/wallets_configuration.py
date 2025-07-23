import json
from enum import Enum
from pathlib import Path
from typing import Any

from wizard.errors import BadConfigurationError


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
            elif kind == WalletKind.PEM:
                entries.append(PEMWalletEntry.new_from_dictionary(entry_raw))
            elif kind == WalletKind.Ledger:
                entries.append(LedgerWalletEntry.new_from_dictionary(entry_raw))
            else:
                raise BadConfigurationError(f"unknown wallet kind: {kind}")

        return WalletsConfiguration(entries)


class WalletEntry:
    def __init__(self, kind: "WalletKind", name: str) -> None:
        self.kind = kind
        self.name = name


class WalletKind(str, Enum):
    Mnemonic = "mnemonic"
    Keystore = "keystore"
    Keystores = "keystores"
    PEM = "pem"
    Ledger = "ledger"


class MnemonicWalletEntry(WalletEntry):
    def __init__(self,
                 name: str,
                 mnemonic: str,
                 mnemonic_file: str,
                 address_indices: list[int]) -> None:
        super().__init__(WalletKind.Mnemonic, name)

        self.mnemonic = mnemonic
        self.mnemonic_file = mnemonic_file
        self.address_indices = address_indices

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.Mnemonic

        name = data.get("name") or ""
        mnemonic = data.get("mnemonic") or ""
        mnemonic_file = data.get("mnemonicFile") or ""
        address_indices = data.get("addressIndices") or []

        return cls(
            name=name,
            mnemonic=mnemonic,
            mnemonic_file=mnemonic_file,
            address_indices=address_indices
        )


class KeystoreWalletEntry(WalletEntry):
    def __init__(self,
                 name: str,
                 file: str,
                 password: str,
                 password_file: str,
                 address_indices: list[int]) -> None:
        super().__init__(WalletKind.Keystore, name)

        self.file = file
        self.password = password
        self.password_file = password_file
        self.address_indices = address_indices

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.Keystore

        name = data.get("name") or ""
        file = data.get("file") or ""
        password = data.get("password") or ""
        password_file = data.get("passwordFile") or ""
        address_indices = data.get("addressIndices") or []

        return cls(
            name=name,
            file=file,
            password=password,
            password_file=password_file,
            address_indices=address_indices
        )


class KeystoresWalletEntry(WalletEntry):
    def __init__(self,
                 name: str,
                 folder: str,
                 unique_password: str,
                 unique_password_file: str) -> None:
        super().__init__(WalletKind.Keystores, name)

        self.folder = folder
        self.unique_password = unique_password
        self.unique_password_file = unique_password_file

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.Keystores

        name = data.get("name") or ""
        folder = data.get("folder") or ""
        unique_password = data.get("uniquePassword") or ""
        unique_password_file = data.get("uniquePasswordFile") or ""

        return cls(
            name=name,
            folder=folder,
            unique_password=unique_password,
            unique_password_file=unique_password_file
        )


class PEMWalletEntry(WalletEntry):
    def __init__(self,
                 name: str,
                 file: str,
                 address_indices: list[int]) -> None:
        super().__init__(WalletKind.PEM, name)

        self.file = file
        self.address_indices = address_indices

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.PEM

        name = data.get("name") or ""
        file = data.get("file") or ""
        address_indices = data.get("addressIndices") or []

        return cls(
            name=name,
            file=file,
            address_indices=address_indices
        )


class LedgerWalletEntry(WalletEntry):
    def __init__(self,
                 name: str,
                 address_indices: list[int]) -> None:
        super().__init__(WalletKind.Ledger, name)

        self.address_indices = address_indices

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.Ledger

        name = data.get("name") or ""
        address_indices = data.get("addressIndices") or []

        return cls(
            name=name,
            address_indices=address_indices
        )
