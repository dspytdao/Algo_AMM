# Automated Prediction Market Maker on Algorand

**NOTE**: This code is not audited and should not be used in production environment.

## Summary

Following this tutorial you can create
an Automated Market Maker for Prediction Market with the help of PyTeal and Py-algorand-sdk.

## Requirements

1. [Vscode](https://code.visualstudio.com/) or another IDE
2. [Python3.10](https://www.python.org/downloads/)
3. [Py-algorand-sdk](https://py-algorand-sdk.readthedocs.io/en/latest/index.html)
4. [PyTEAL](https://pyteal.readthedocs.io/en/stable/installation.html)
5. [Algorand Sandbox](https://github.com/algorand/sandbox) or connect to Algorand Node through [Purestake](https://developer.purestake.io/)

## Background

PyTeal is a python library for generating TEAL programs. PyTeal is used for writing smart contracts on the Algorand blockchain. The TEAL code will be deployed using the Algorand JavaScript SDK.

To interact with the smart contract the Python SDK will be used to compile and deploy the PyTeal smart contract code.

The goal of the Automated Market Maker contract is to configure and create a Liquidity Pool, which allows users to purchase and redeem spawned tokens once the event has been realised.

The Liqudity Pool supports a constant reserve ratio for stable price discovery and protection of users.

The liquidity provided allows to spawn two tokens in equal amount, representing binary outcomes.
Once the event has occured the price for one token should resolve to 1, while 0 for another.

Funds can only be released after the creator of the contract assinged the outcome.

## Steps

## Installing with Virtual environment

```bash
pip install virtualenv
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Useful Resources

[PyTEAL](https://pyteal.readthedocs.io/en/stable/index.html)

[Testnet Dispensary](https://dispenser.testnet.aws.algodev.network/)

[Py-algorand-sdk](https://py-algorand-sdk.readthedocs.io/en/latest/index.html)

[AlgoExplorer](https://testnet.algoexplorer.io/address/)

[Algorand: Build with Python](https://developer.algorand.org/docs/get-started/dapps/pyteal/)

[Alogrand: Smart contract details](https://developer.algorand.org/docs/get-details/dapps/smart-contracts/apps/)

[Amm Demo contract](https://github.com/maks-ivanov/amm-demo/blob/main/amm/contracts/contracts.py)

[Creating Stateful Algorand Smart Contracts in Python with PyTeal](https://developer.algorand.org/articles/creating-stateful-algorand-smart-contracts-python-pyteal/)
