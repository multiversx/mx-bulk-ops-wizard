# mx-rewards-collector

Utility scripts for collecting (claiming) staking rewards.

## Python Virtual environment

Create a virtual environment and install the dependencies:

```
python3 -m venv ./venv
source ./venv/bin/activate
pip install -r ./requirements.txt --upgrade
```

## Configure wallets

Wallets are configured in a `.json` file.

Supposing you have the [mx-sdk-testwallets](https://github.com/multiversx/mx-sdk-testwallets) repository (the MultiversX test wallets) cloned into the `$HOME` directory.

Here's what a wallet configuration file would look like:

```
[
    {
        "kind": "mnemonic",
        "mnemonic": "moral volcano peasant pass circle pen over picture flat shop clap goat never lyrics gather prepare woman film husband gravity behind test tiger improve",
        "addressIndices": [0, 1, 2, 3]
    },
    {
        "kind": "mnemonic",
        "mnemonicFile": "~/mx-sdk-testwallets/users/mnemonic.txt",
        "addressIndices": [4, 5]
    },
    {
        "kind": "keystore",
        "file": "~/mx-sdk-testwallets/users/alice.json",
        "password": "password",
        "addressIndices": []
    },
    {
        "kind": "keystore",
        "file": "~/mx-sdk-testwallets/users/bob.json",
        "passwordFile": "~/mx-sdk-testwallets/users/password.txt",
        "addressIndices": []
    },
    {
        "kind": "keystores",
        "folder": "~/mx-sdk-testwallets/users",
        "uniquePasswordFile": "~/mx-sdk-testwallets/users/password.txt"
    },
    {
        "name": "whale",
        "kind": "pem",
        "file": "~/whale.pem"
    },
    {
        "kind": "ledger",
        "addressIndices": [0, 1, 2, 3]
    }
]
```

## Setup environment variables

Custom URLs for API & Proxy, if default ones are not sufficient (for example, due to rate limiting) - if set, they are taken into consideration by the scripts, under the hood:

```
export MAINNET_PROXY_URL="..."
export MAINNET_API_URL="..."
```

Path towards the wallet configuration file (not handled internally, defined for example purposes):

```
export WALLETS_CONFIG="./collector/testdata/wallets.config.json"
```

Receiver of the rewards (not handled internally, defined for example purposes):

```
export RECEIVER="erd1testnlersh4z0wsv8kjx39me4rmnvjkwu8dsaea7ukdvvc9z396qykv7z7"
```

## Claim rewards (delegation)

```
PYTHONPATH=. python3 ./collector/claim_rewards.py --network=devnet --wallets=$WALLETS_CONFIG --threshold=0
```

## Claim rewards (legacy delegation)

```
PYTHONPATH=. python3 ./collector/claim_rewards_legacy.py --network=devnet --wallets=$WALLETS_CONFIG --threshold=1
```

## Summarize previously claimed (received) rewards

```
PYTHONPATH=. python3 ./collector/collect_rewards.py --network=devnet --wallets=$WALLETS_CONFIG --after-epoch=3000 --outfile=rewards.json
```

## Prepare amounts to transfer

```
PYTHONPATH=. python3 ./collector/prepare_transfers.py --threshold=1 --infile=rewards.json --outfile=transfers.json
```

## Transfer amounts to an account

```
PYTHONPATH=. python3 ./collector/do_transfers.py --network=devnet --wallets=$WALLETS_CONFIG --infile=transfers.json --receiver=${RECEIVER}
```

## Vote on governance

```
export PROOFS="./proofs.json"
PYTHONPATH=. python3 ./collector/vote_on_governance.py --network=devnet --wallets=$WALLETS_CONFIG --proofs=${PROOFS}
```

## Guardians

For the examples below, we'll consider:

```
export WALLETS_CONFIG="./collector/testdata/wallets#foo.config.json"
export AUTH_REGISTRATION="./collector/testdata/auth.json"
```

Get guardians status:

```
PYTHONPATH=. python3 ./collector/guardians_status.py --network=testnet --wallets=$WALLETS_CONFIG
```

If an `auth.json` registration file is already available, then:

```
PYTHONPATH=. python3 ./collector/guardians_status.py --network=testnet --wallets=$WALLETS_CONFIG --auth=$AUTH_REGISTRATION
```

Register accounts on **trusted cosigner service**:

```
PYTHONPATH=. python3 ./collector/guardians_register.py --network=testnet --wallets=$WALLETS_CONFIG --auth=$AUTH_REGISTRATION
```

Above, we are required to pass the path towards an auth registration file. If the file is missing, it will be created. If it exists, it will be updated in-place.

Set guardians (sign & broadcast transactions), given an auth registration file:

```
PYTHONPATH=. python3 ./collector/guardians_set.py --network=testnet --wallets=$WALLETS_CONFIG --auth=$AUTH_REGISTRATION
```

Guard accounts (sign & broadcast transactions), given an auth registration file:

```
PYTHONPATH=. python3 ./collector/guardians_guard.py --network=testnet --wallets=$WALLETS_CONFIG --auth=$AUTH_REGISTRATION
```
