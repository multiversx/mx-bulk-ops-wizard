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
