# Automated Prediction Market Maker on Algorand

**NOTE**: This code is not audited and should not be used in production environment.

## Summary

Following this tutorial you can create
an Automated Market Maker for Prediction Market with the help of PyTeal and Py-algorand-sdk.

## Requirements

1. [Vscode](https://code.visualstudio.com/) or another IDE
2. [Python3.10](https://www.python.org/downloads/)
3. [PIP Package Manager](https://pip.pypa.io/en/stable/)
4. [Py-algorand-sdk](https://py-algorand-sdk.readthedocs.io/en/latest/index.html)
5. [PyTEAL](https://pyteal.readthedocs.io/en/stable/installation.html)
6. [Algorand Sandbox](https://github.com/algorand/sandbox) or connect to Algorand Node through [Purestake](https://developer.purestake.io/)

## Background

PyTeal is a python library for generating TEAL programs. PyTeal is used for writing smart contracts on the Algorand blockchain. The TEAL code will be deployed using the Algorand JavaScript SDK.

To interact with the smart contract the Python SDK will be used to compile and deploy the PyTeal smart contract code.

The goal of the Automated Market Maker contract is to configure and create a Liquidity Pool, which allows users to purchase and redeem spawned tokens once the event has been realised.

The Liqudity Pool supports a constant reserve ratio for stable price discovery and protection of users.

The liquidity provided allows to spawn two tokens in equal amount, representing binary outcomes.
Once the event has occured the price for one token should resolve to 1, while 0 for another.

Funds can only be released after the creator of the contract assinged the outcome.

Code is available at this GitHub Repository.

## Steps

# Project Setup

We setup Python virtual environment. The following commands will install and activate the virtual environment and then install needed dependencies.

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

To write PyTeal code we create a new directory and `amm.py config.py helpers.py __init__.py` files:

```bash
mkdir contracts
cd contracts
touch amm.py config.py helpers.py __init__.py
```

# PyTeal Contract Configuration File

In `config.py` we contain the global variables, except for `TOKEN_DEFAULT_AMOUNT`, to congifure the smart contract.

```python
from pyteal import Bytes, Int

CREATOR_KEY = Bytes("creator_key")

RESULT = Bytes("result")

TOKEN_FUNDING_KEY = Bytes("token_funding_key")
TOKEN_FUNDING_RESERVES = Bytes("token_funding_reserves")

POOL_FUNDING_RESERVES = Bytes("pool_funding_reserves")

POOL_TOKEN_KEY = Bytes("pool_token_key")
POOL_TOKENS_OUTSTANDING_KEY = Bytes("pool_tokens_outstanding_key")

YES_TOKEN_KEY = Bytes("yes_token_key")
YES_TOKENS_OUTSTANDING_KEY = Bytes("yes_tokens_outstanding_key")
YES_TOKENS_RESERVES = Bytes("yes_tokens_reserves")

NO_TOKEN_KEY = Bytes("no_token_key")
NO_TOKENS_OUTSTANDING_KEY = Bytes("no_tokens_outstanding_key")
NO_TOKENS_RESERVES = Bytes("no_tokens_reserves")

MIN_INCREMENT_KEY = Bytes("min_increment_key")

TOKEN_DEFAULT_AMOUNT = Int(10 ** 13)
```

These variables can be imported as:

```python
from contracts.config import (
    CREATOR_KEY, TOKEN_FUNDING_KEY,
    POOL_TOKEN_KEY, MIN_INCREMENT_KEY,
    POOL_TOKENS_OUTSTANDING_KEY, TOKEN_DEFAULT_AMOUNT,
    YES_TOKEN_KEY, NO_TOKEN_KEY,
    TOKEN_FUNDING_RESERVES, POOL_FUNDING_RESERVES,
    RESULT
)
```

# Main Conditional

```python
    on_call_method = Txn.application_args[0]

    on_call = Cond(
        [on_call_method == Bytes("setup"), on_setup],
        [on_call_method == Bytes("supply"), on_supply],
        [on_call_method == Bytes("withdraw"), on_withdraw],
        [on_call_method == Bytes("redeem"), on_redemption],
        [on_call_method == Bytes("result"), on_result],
        [on_call_method == Bytes("swap"), on_swap],
    )

    program = Cond(
        [Txn.application_id() == Int(0), on_create],
        [Txn.on_completion() == OnComplete.NoOp, on_call],
        [Txn.on_completion() == OnComplete.DeleteApplication, on_delete],
        [
            Or(
                Txn.on_completion() == OnComplete.OptIn,
                Txn.on_completion() == OnComplete.CloseOut,
                Txn.on_completion() == OnComplete.UpdateApplication,
            ),
            Reject(),
        ],
    )
```

This statement is the heart of the smart contract. Based on how the contract is called, it chooses which operation to run. For example, if `Txn.application_id()` is 0, then the code from `on_create` runs. If `Txn.on_completion()` is `OnComplete.NoOp`, then `on_call` runs. If `Txn.application_args[0]` is "setup", then `on_setup` runs. If either `Txn.on_completion()` are `OnComplete.OptIn`,`OnComplete.CloseOut`,`OnComplete.UpdateApplication` or none of the described cases are true, the program will exit an with error. Let’s look at each of these cases below.

# On create

```python
    on_create = Seq(
        App.globalPut(CREATOR_KEY, Txn.application_args[0]),
        App.globalPut(TOKEN_FUNDING_KEY, Btoi(Txn.application_args[1])),
        App.globalPut(MIN_INCREMENT_KEY, Btoi(Txn.application_args[2])),
        App.globalPut(TOKEN_FUNDING_RESERVES, Int(0)),
        App.globalPut(POOL_FUNDING_RESERVES, Int(0)),
        App.globalPut(RESULT, Int(0)),
        Approve(),
    )
```

This part of the program is responsible for setting up the initial state of the smart contract. It writes the keys to its global state.

The values of `CREATOR_KEY`,`TOKEN_FUNDING_KEY` and `MIN_INCREMENT_KEY` keys are determined by the application call arguments from the `Txn.application_args` list. Meanhwile, `TOKEN_FUNDING_RESERVES`, `POOL_FUNDING_RESERVES` and `RESULT` are initialised as 0 integer values.

# On setup

```python
def get_setup():
    pool_token_id = App.globalGetEx(Global.current_application_id(), POOL_TOKEN_KEY)
    pool_tokens_outstanding = App.globalGetEx(
        Global.current_application_id(), POOL_TOKENS_OUTSTANDING_KEY
    )
    return Seq(
        pool_token_id,
        pool_tokens_outstanding,
        Assert(Not(pool_token_id.hasValue())),
        Assert(Not(pool_tokens_outstanding.hasValue())),
        createPoolToken(TOKEN_DEFAULT_AMOUNT),
        optIn(TOKEN_FUNDING_KEY),
        createNoToken(TOKEN_DEFAULT_AMOUNT),
        optIn(NO_TOKEN_KEY),
        createYesToken(TOKEN_DEFAULT_AMOUNT),
        optIn(YES_TOKEN_KEY),
        Approve(),
    )
```

This code runs when an account calls `Txn.application_args[0]` that is `Bytes("setup")` into the smart contract. It returns true if the current pool token has no been created and has no outstanding tokens, meaning that it can only be set up once.

The methods create pool token, yes and no tokens, which the contract opts in the application.

```python
def createPoolToken(pool_token_amount: TealType.uint64) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_total: pool_token_amount,
                TxnField.config_asset_name: Bytes("PoolToken"),
                TxnField.config_asset_default_frozen: Int(0),
                TxnField.config_asset_decimals: Int(0),
                TxnField.config_asset_reserve: Global.current_application_address(),
            }
        ),
        InnerTxnBuilder.Submit(),
        App.globalPut(POOL_TOKEN_KEY, InnerTxn.created_asset_id()),
        App.globalPut(POOL_TOKENS_OUTSTANDING_KEY, Int(0)),
    )

def optIn(token_key: TealType.bytes) -> Expr:
    return sendToken(token_key, Global.current_application_address(), Int(0))

def sendToken(
    token_key: TealType.bytes, receiver: TealType.bytes, amount: TealType.uint64
) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: App.globalGet(token_key),
                TxnField.asset_receiver: receiver,
                TxnField.asset_amount: amount,
            }
        ),
        InnerTxnBuilder.Submit(),
    )

def createNoToken(token_amount: TealType.uint64) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_total: token_amount,
                TxnField.config_asset_name: Bytes("NoToken"),
                TxnField.config_asset_unit_name: Bytes("No"),
                TxnField.config_asset_default_frozen: Int(0),
                TxnField.config_asset_decimals: Int(0),
                TxnField.config_asset_reserve: Global.current_application_address(),
            }
        ),
        InnerTxnBuilder.Submit(),
        App.globalPut(NO_TOKEN_KEY, InnerTxn.created_asset_id()),
        App.globalPut(NO_TOKENS_OUTSTANDING_KEY, Int(0)),
        App.globalPut(NO_TOKENS_RESERVES, Int(0)),
    )

def createYesToken(token_amount: TealType.uint64) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_total: token_amount,
                TxnField.config_asset_name: Bytes("YesToken"),
                TxnField.config_asset_unit_name: Bytes("Yes"),
                TxnField.config_asset_default_frozen: Int(0),
                TxnField.config_asset_decimals: Int(0),
                TxnField.config_asset_reserve: Global.current_application_address(),
            }
        ),
        InnerTxnBuilder.Submit(),
        App.globalPut(YES_TOKEN_KEY, InnerTxn.created_asset_id()),
        App.globalPut(YES_TOKENS_OUTSTANDING_KEY, Int(0)),
        App.globalPut(YES_TOKENS_RESERVES, Int(0)),
    )
```

# On supply

# 7. Create Account

To deploy a smart contract we create an account and fund it using [Testnet Dispensary](https://dispenser.testnet.aws.algodev.network/).

```python
from algosdk import account

# generate an account
private_key, address = account.generate_account()
print("Private key:", private_key)
print("Address:", address)
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
