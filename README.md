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

```
```

## Setup environment

```
WALLETS_CONFIG="./collector/testdata/wallets.config.json"
```

## Claim rewards

```
PYTHONPATH=. python3 ./collector/claim_rewards.py --network=devnet --wallets=$WALLETS_CONFIG --threshold=0
```
