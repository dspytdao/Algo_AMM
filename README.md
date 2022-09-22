# Automated Prediction Market Maker on Algorand

**NOTE**: This code is not audited and should not be used in production environment.

## Summary

Algo AMM allows you to trade on the outcomes of events, and follow the odds to garner accurate insights about the future.

Liquidity Providers supply stable coins in return for the liquidity shares.

The liquidity lets users to buy or sell Voting Shares, which are redeemed for 1 unit of the stable asset if the outcome is resolved as correct, and become worthless if it’s incorrect.

The core feature of the app is that we protect the owners of Voting shares by keeping the reserves of stable assets, primarily in case of liquidity drain.

The goal is, by harnessing the power of free markets to aggregate collective knowledge and provide the general public with an unbiased source of truth in regards to the likelihood of certain significant events happening in the future.

![](https://imgur.com/HILKB03.png)

[![Algo AMM](https://yt-embed.herokuapp.com/embed?v=uePtNvBP3oQ)](https://youtu.be/uePtNvBP3oQ "Algo AMM")

[Project Slides Deck](https://docs.google.com/presentation/d/1FBchISurC6Fsy-iEkmQ4gggEs7i6D4pRHab8gwOEyqk/edit?usp=sharing)

We wrote contract for Prediction Market Constant Function Automated Market Maker with the help of PyTeal and Py-algorand-sdk.

The front end application is written with react and vite.
The repository for the Front-End is avalaible here: https://github.com/dspytdao/algo-amm-frontend

## Overview

Constant Function Automated Market Maker (AMM) contract provides configuration options and creates a market for an event that has a binary outcome.

Liquidity Pool provides a foundation for users to purchase and redeem spawned tokens once the event has been resolved. The Liquidity Pool supports a constant reserve ratio for stable price discovery and protection from liquidity drain. The liquidity provided allows to spawn two tokens in equal amount in 25%/25% proportion of the liquidity supplied.

The purchase price for each token is determined by equation: x + y = k. Where x is the amount of A tokens in the AMM, y is the amount of B tokens in the AMM.

Once the event has occured the price for one token should resolve to 1, while 0 for another.

Liquidity Shares and Voting Shares can only be released after the creator of the contract moderated the outcome.

## Requirements

1. [Vscode](https://code.visualstudio.com/) or another IDE
2. [Python3.10](https://www.python.org/downloads/)
3. [PIP Package Manager](https://pip.pypa.io/en/stable/)
4. [Py-algorand-sdk](https://py-algorand-sdk.readthedocs.io/en/latest/index.html)
5. [PyTEAL](https://pyteal.readthedocs.io/en/stable/installation.html)
6. Algorand [Purestake node](https://developer.purestake.io/)

## Background

PyTeal is a python library for generating TEAL programs. PyTeal is used for writing smart contracts on the Algorand blockchain.
To interact with the smart contract the Python SDK will be used to compile and deploy the PyTeal smart contract code.

# Project Setup

We setup Python virtual environment. The following commands will install and activate the virtual environment and then install dependencies.

## Installing with Virtual environment

```bash
pip install virtualenv
virtualenv venv
source venv/bin/activate
pip install pyteal
```

![https://imgur.com/pgG6fin.png](https://imgur.com/pgG6fin.png)

`deactivate` to deactivate the virtual environment.

`source venv/bin/activate` to activate virtualenv once again. Replace bin with Scripts on Windows.

# PyTeal AMM Smart Contract

PyTeal contracts are written in Python using any editor of your choice. `compileProgram` method produces the TEAL code which is then compiled into bytecode and deployed to the blockchain.

The PyTeal smart contract consists of two programs. These are called the approval program and the clear programs. In PyTeal both of these programs are generally created in the same Python file.

The `approval_program` is responsible for processing all application calls to the contract, with the exception of the clear call. The program is responsible for implementing most of the logic of an application.

The `clear_program` is used to handle accounts using the clear call to remove the smart contract from their balance record.

In `amm.py` we keep the high-level logic of the contract, `helpers.py` contains lower level methods and `config.py` keeps track of global variable and key configuration variables.

## Useful Resources

[PyTEAL](https://pyteal.readthedocs.io/en/stable/index.html)

[Testnet Dispensary](https://dispenser.testnet.aws.algodev.network/)

[Py-algorand-sdk](https://py-algorand-sdk.readthedocs.io/en/latest/index.html)

[AlgoExplorer](https://testnet.algoexplorer.io/address/)

[Algorand: Build with Python](https://developer.algorand.org/docs/get-started/dapps/pyteal/)

[Alogrand: Smart contract details](https://developer.algorand.org/docs/get-details/dapps/smart-contracts/apps/)

[Amm Demo contract](https://github.com/maks-ivanov/amm-demo/blob/main/amm/contracts/contracts.py)

[Creating Stateful Algorand Smart Contracts in Python with PyTeal](https://developer.algorand.org/articles/creating-stateful-algorand-smart-contracts-python-pyteal/)
