import json
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from collector.errors import BadConfigurationError


class WalletsConfiguration:
    def __init__(self, entries: list["WalletEntry"]) -> None:
        self.entries = entries

    @classmethod
    def new_from_file(cls, path: Path):
        path = path.expanduser().resolve()
        verify_file(path, ".json")
        content = path.read_text()
        entries_raw: list[dict[str, Any]] = json.loads(content)
        entries: list[WalletEntry] = []

        for entry_raw in entries_raw:
            kind = entry_raw.get("kind")

            if kind == WalletKind.Mnemonic:
                entries.append(MnemonicWalletEntry.new_from_dictionary(entry_raw))
            elif kind == WalletKind.Mnemonics:
                raise NotImplementedError()
            elif kind == WalletKind.Keystore:
                entries.append(KeystoreWalletEntry.new_from_dictionary(entry_raw))
            elif kind == WalletKind.Keystores:
                entries.append(KeystoresWalletEntry.new_from_dictionary(entry_raw))

        return WalletsConfiguration(entries)


class WalletEntry:
    def __init__(self, kind: "WalletKind") -> None:
        self.kind = kind


class WalletKind(str, Enum):
    Mnemonic = "mnemonic"
    Mnemonics = "mnemonics"
    Keystore = "keystore"
    Keystores = "keystores"
    Ledger = "ledger"


class MnemonicWalletEntry(WalletEntry):
    def __init__(self,
                 mnemonic: Optional[str],
                 mnemonic_path: Optional[str],
                 address_indices: Optional[list[int]] = None) -> None:
        super().__init__(WalletKind.Mnemonic)

        is_mnemonic_missing = not mnemonic and not mnemonic_path
        is_mnemonic_overconfigured = mnemonic and mnemonic_path

        if is_mnemonic_missing or is_mnemonic_overconfigured:
            raise BadConfigurationError("either 'mnemonic' or 'mnemonic path' must be set")

        # if mnemonic_path:
        #     self.mnemonic_path = Path(mnemonic_path).expanduser().resolve()
        #     verify_file(self.mnemonic_path, ".txt")

        self.mnemonic = mnemonic
        self.mnemonic_path = mnemonic_path
        self.address_indices = address_indices or [0]

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.Mnemonic

        mnemonic = data.get("mnemonic") or ""
        mnemonic_path = data.get("mnemonicPath") or ""
        address_indices = data.get("addressIndices")

        return cls(
            mnemonic=mnemonic,
            mnemonic_path=mnemonic_path,
            address_indices=address_indices
        )


class KeystoreWalletEntry(WalletEntry):
    def __init__(self,
                 path: str,
                 password: Optional[str],
                 password_path: Optional[str],
                 address_indices: Optional[list[int]] = None) -> None:
        super().__init__(WalletKind.Keystore)

        if not path:
            raise BadConfigurationError("for wallet kind = <keystore>, 'path' must be set")

        is_password_missing = not password and not password_path
        is_password_overconfigured = password and password_path

        if is_password_missing or is_password_overconfigured:
            raise BadConfigurationError("either 'password' or 'password path' must be set")

        self.path = Path(path).expanduser().resolve()
        verify_file(self.path, ".json")

        self.password = password

        if password_path:
            self.password_path = Path(password_path).expanduser().resolve()
            verify_file(self.password_path, ".txt")

        self.address_indices = address_indices or [0]

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.Keystore

        path = data.get("path") or ""
        password = data.get("password") or ""
        password_path = data.get("passwordPath") or ""
        address_indices = data.get("addressIndices")

        return cls(
            path=path,
            password=password,
            password_path=password_path,
            address_indices=address_indices
        )


class KeystoresWalletEntry(WalletEntry):
    def __init__(self) -> None:
        super().__init__(WalletKind.Keystores)

    @classmethod
    def new_from_dictionary(cls, data: dict[str, Any]):
        assert data["kind"] == WalletKind.Keystores

        path = data.get("path") or ""
        password = data.get("password") or ""
        password_path = data.get("passwordPath") or ""
        address_indices = data.get("addressIndices")

        return cls()


def verify_file(path: Path, required_suffix: str):
    if not path.exists():
        raise BadConfigurationError(f"file {path} cannot be found")

    if path.suffix != required_suffix:
        raise BadConfigurationError(f"file {path} must have the suffix {required_suffix}")
