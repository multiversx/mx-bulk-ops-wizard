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

Custom URLs for API & Proxy, if default ones are not sufficient (for example, due to rate limiting):

```
export MAINNET_PROXY_URL="..."
export MAINNET_API_URL="..."
```

```
WALLETS_CONFIG="./collector/testdata/wallets.config.json"
```

## Claim rewards (delegation)

```
PYTHONPATH=. python3 ./collector/claim_rewards.py --network=devnet --wallets=$WALLETS_CONFIG --threshold=0
```

## Claim rewards (legacy delegation)

```
PYTHONPATH=. python3 ./collector/claim_rewards_legacy.py --network=devnet --wallets=$WALLETS_CONFIG --threshold=1
```

## Collect previously received rewards

```
PYTHONPATH=. python3 ./collector/collect_rewards.py --network=devnet --wallets=$WALLETS_CONFIG --threshold=1 --after-epoch=3000 --outfile=rewards.json
```
