# Automated Prediction Market Maker on Algorand

**NOTE**: This code is not audited and should not be used in production environment.

## Summary

Algo AMM is an automated prediction market maker on Algorand that allows users to trade on the outcomes of events, and follow the odds to garner accurate insights about the future.

Our target market is traders, speculators and investors who are interested in taking advantage of the predictive power of markets. The user problem we are addressing is the difficulty in predicting outcomes of events accurately and reliably. Our solution is an automated prediction market maker that allows users to trade on the outcomes of events, and follow the odds to garner accurate insights about the future. We provide liquidity for users to buy or sell Voting Shares, which can be redeemed for 1 unit of the stable asset if the outcome is resolved as correct, and become worthless if it’s incorrect.

The goal is, by harnessing the power of free markets to aggregate collective knowledge and provide the general public with an unbiased source of truth in regards to the likelihood of certain significant events happening in the future.

![Automated Market Maker](/assets/AMM.png)

[Project Slides Deck](https://docs.google.com/presentation/d/1FBchISurC6Fsy-iEkmQ4gggEs7i6D4pRHab8gwOEyqk/)

We wrote contract for Prediction Market Constant Function Automated Market Maker with the help of `PyTeal` and `Py-algorand-sdk`.

The front end application is written with react and vite.

[The repository for the front-end](https://github.com/dspytdao/algo-amm-frontend)

[AlgoAMM Live](https://algoamm.com)

## Founders

Pavel Fedotov: [LinkedIn](https://www.linkedin.com/in/pavel-fedotov-pinsave/) [Twitter](https://twitter.com/pfedprog) [GitHub](https://github.com/pfed-prog/)

Grigore Gabriel Trifan: [LinkedIn](https://www.linkedin.com/in/grigore-trifan-666biyz/) [Twitter](https://twitter.com/grigore_trifan) [GitHub](https://github.com/GregTrifan)

## Overview

Constant Function Automated Market Maker (AMM) contract provides configuration options and creates a market for an event that has a binary outcome.

Liquidity Pool provides a foundation for users to purchase and redeem spawned tokens once the event has been resolved. The Liquidity Pool supports a constant reserve ratio for stable price discovery and protection from liquidity drain. The liquidity provided allows to spawn two tokens in equal amount in 25%/25% proportion of the liquidity supplied.

The purchase price for each token is determined by equation: x + y = k. Where x is the amount of A tokens in the AMM, y is the amount of B tokens in the AMM.

Once the event has occurred the price for one token should resolve to 1, while 0 for another.

Liquidity Shares and Voting Shares can only be released after the creator of the contract moderated the outcome.

As a prediction market maker on Algorand, our primary role would be to provide liquidity to users who are looking to buy and sell prediction market tokens on the platform. This involves creating markets for events or outcomes, such as the winner of a political election or the outcome of a sports game, and setting prices for these tokens based on supply and demand.

## Requirements

1. [Vscode](https://code.visualstudio.com/) or another IDE
2. [Python 3](https://www.python.org/downloads/)
3. [PIP Package Manager](https://pip.pypa.io/en/stable/)
4. [Py-algorand-sdk](https://py-algorand-sdk.readthedocs.io/en/latest/index.html)
5. [PyTEAL](https://pyteal.readthedocs.io/en/stable/installation.html)
6. Algorand [Purestake node api key](https://developer.purestake.io/)

## PyTeal AMM Smart Contract

PyTeal contracts are written in Python using any editor of your choice. `compileProgram` method produces the TEAL code which is then compiled into bytecode and deployed to the blockchain.

The PyTeal smart contract consists of two programs. These are called the approval program and the clear programs. In PyTeal both of these programs are generally created in the same Python file.

The `approval_program` is responsible for processing all application calls to the contract, with the exception of the clear call. The program is responsible for implementing most of the logic of an application.

The `clear_program` is used to handle accounts using the clear call to remove the smart contract from their balance record.

In `amm.py` we keep the high-level logic of the contract, `helpers.py` contains lower level methods and `config.py` keeps track of global variable and key configuration variables.

## Useful Resources

[PyTEAL](https://pyteal.readthedocs.io/en/stable/index.html)

[Testnet Dispensary](https://dispenser.testnet.aws.algodev.network/)

[Algorand Dispenser](https://bank.testnet.algorand.network/)

[Py-algorand-sdk](https://py-algorand-sdk.readthedocs.io/en/latest/index.html)

[AlgoExplorer](https://testnet.algoexplorer.io/address/)

[Algorand: Build with Python](https://developer.algorand.org/docs/get-started/dapps/pyteal/)

[Algorand: Smart contract details](https://developer.algorand.org/docs/get-details/dapps/smart-contracts/apps/)

[Amm Demo contract](https://github.com/maks-ivanov/amm-demo/blob/main/amm/contracts/contracts.py)

[Creating Stateful Algorand Smart Contracts in Python with PyTeal](https://developer.algorand.org/articles/creating-stateful-algorand-smart-contracts-python-pyteal/)

[How to publish PIP package](https://shobhitgupta.medium.com/how-to-publish-your-own-pip-package-560bde836b17)

[Algorand Ecosystem Algo AMM page](https://ecosystem.algorand.com/project/algo-amm)

[How To Use unittest to Write a Test Case for a Function in Python](https://www.digitalocean.com/community/tutorials/how-to-use-unittest-to-write-a-test-case-for-a-function-in-python)

## More Information about Dspyt

[Dspyt Homepage](https://dspyt.com)

[Dspyt GitHub DAO Page](https://github.com/dspytdao)
