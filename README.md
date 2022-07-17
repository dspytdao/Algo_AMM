# Automated Prediction Market Maker on Algorand

**NOTE**: This code is not audited and should not be used in production environment.

## Summary

We built Automated Prediction Market Maker on Algorand.

The application lets people trade on the outcomes of events, and follow the odds to garner accurate insights about the future. Users buy or sell Voting Shares, which can be redeemed for 1 unit of the stable asset if the outcome is resolved as correct, and become worthless if it’s incorrect. Owners of outcome shares are never locked in and can sell their position at any time. The goal is, by harnessing the power of free markets to aggregate collective knowledge and provide the general public with an unbiased source of truth in regards to the likelihood of certain significant events happening in the future.

We wrote contract for Prediction Market Constant Function Automated Market Maker with the help of PyTeal and Py-algorand-sdk.

The front end application is written with react and vite.

## Overview

Constant Function Automated Market Maker (AMM) contract provides configuration option and creates a market for an event that has a binary outcome.

Liquidity Pool provides a foundation for users to purchase and redeem spawned tokens once the event has been resolved. The Liquidity Pool supports a constant reserve ratio for stable price discovery and protection of users. The liquidity provided allows to spawn two tokens in equal amount in 50%/50% of the liquidity supplied,

The two tokens represent binary outcomes. Once the event has occured the price for one token should resolve to 1, while 0 for another. The purchase price for each token is determined by equation: x + y = k. Where x is the amount of A tokens in the AMM, y is the amount of B tokens in the AMM.

Funds can only be released after the creator of the contract moderated the outcome.

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

Code is available at this GitHub Repository.

# Steps

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

In `amm.py` we will keep the high-level logic of the contract, `helpers.py` will contain lower level methods and `config.py` will keep track of global variable and key configuration variables.

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

    on_setup = Seq(
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
    return on_setup
```

This code runs when an account calls `Txn.application_args[0]` that equals to `Bytes("setup")` into the smart contract. It returns true if the current pool token has not been created and there are no outstanding tokens, meaning that the smart contract can only be set up once.

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

```python
def get_supply():
    token_txn_index = Txn.group_index() - Int(1)

    on_supply = Seq(
        Assert(
            And(
                validateTokenReceived(token_txn_index, TOKEN_FUNDING_KEY),
                Gtxn[token_txn_index].asset_amount()
                >= App.globalGet(MIN_INCREMENT_KEY),
           )
        ),
        mintAndSendPoolToken(
            Txn.sender(),
            Gtxn[token_txn_index].asset_amount(),
        ),
        Approve(),
    )
    return on_supply
```

This code runs when an account calls `Txn.application_args[0]` that equals to `Bytes("supply")` into the smart contract. It returns true if the token received by the smart contract is the same funding (reserve) token declared in the `on_create` part of the program and is larger in quantity than the minimum value.

`validateTokenReceived` validates the transfer of the tokens.
`mintAndSendPoolToken` keeps track of the pool funding reserves and disburses the pool token based on the proportion of the provided to the exisitng funds.

```python
def validateTokenReceived(
    transaction_index: TealType.uint64, token_key: TealType.bytes
) -> Expr:
    return And(
        Gtxn[transaction_index].type_enum() == TxnType.AssetTransfer,
        Gtxn[transaction_index].sender() == Txn.sender(),
        Gtxn[transaction_index].asset_receiver()
        == Global.current_application_address(),
        Gtxn[transaction_index].xfer_asset() == App.globalGet(token_key),
        Gtxn[transaction_index].asset_amount() > Int(0),
    )

def mintAndSendPoolToken(receiver: TealType.bytes, amount: TealType.uint64) -> Expr:
    return Seq(
        If(App.globalGet(POOL_FUNDING_RESERVES) > Int(0))
        .Then(
            Seq(
                sendToken(POOL_TOKEN_KEY, receiver, amount * App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) / App.globalGet(POOL_FUNDING_RESERVES) ),
                App.globalPut(
                    POOL_TOKENS_OUTSTANDING_KEY,
                App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) + amount * App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) / App.globalGet(POOL_FUNDING_RESERVES)
            ))
        )
        .ElseIf(App.globalGet(POOL_FUNDING_RESERVES) == Int(0))
        .Then(
            Seq(
                sendToken(POOL_TOKEN_KEY, receiver, amount ),
                App.globalPut(
                    POOL_TOKENS_OUTSTANDING_KEY,
                    App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) + amount,
                ),
            )
        ),
        App.globalPut(NO_TOKENS_RESERVES,  amount / Int(4) + App.globalGet(NO_TOKENS_RESERVES) ),
        App.globalPut(YES_TOKENS_RESERVES, amount / Int(4) + App.globalGet(YES_TOKENS_RESERVES) ),
        App.globalPut(
            POOL_FUNDING_RESERVES, App.globalGet(POOL_FUNDING_RESERVES) + amount
        ),
    )
```

# On Withdraw

```python
def get_withdraw():
    pool_token_txn_index = Txn.group_index() - Int(1)

    on_withdraw = Seq(
        Assert(
            validateTokenReceived(pool_token_txn_index, POOL_TOKEN_KEY)
        ),
        withdrawLPToken(
            Txn.sender(),
            Gtxn[pool_token_txn_index].asset_amount(),
        ),
        Approve(),
    )

    return on_withdraw
```

The code runs when an account calls `Txn.application_args[0]` that equals to `Bytes("withdraw")` into the smart contract. It returns true if the token received by the smart contract is the same pool token created in the `on_create` part of the program.

`withdrawLPToken` sends the proportional amount of funding (reserve) token to outstanding pool token, supplied pool tokens and funding reserves.

```python
def withdrawLPToken(
    receiver: TealType.bytes,
    pool_token_amount: TealType.uint64,
) -> Expr:

    return Seq(
        sendToken(
            TOKEN_FUNDING_KEY,
            receiver,
            App.globalGet(POOL_FUNDING_RESERVES) * pool_token_amount / App.globalGet(POOL_TOKENS_OUTSTANDING_KEY),
        ),
        App.globalPut(
            POOL_FUNDING_RESERVES, App.globalGet(POOL_FUNDING_RESERVES) - (App.globalGet(POOL_FUNDING_RESERVES) * pool_token_amount / App.globalGet(POOL_TOKENS_OUTSTANDING_KEY)),
        ),
        App.globalPut(
            POOL_TOKENS_OUTSTANDING_KEY,
            App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) - pool_token_amount,
        ),
        If(App.globalGet(RESULT)==Int(0)).Then(
            Seq(
                App.globalPut(NO_TOKENS_RESERVES,  App.globalGet(NO_TOKENS_RESERVES) - (App.globalGet(POOL_FUNDING_RESERVES) * pool_token_amount / App.globalGet(POOL_TOKENS_OUTSTANDING_KEY)) / Int(4) ),
                App.globalPut(YES_TOKENS_RESERVES, App.globalGet(YES_TOKENS_RESERVES) - (App.globalGet(POOL_FUNDING_RESERVES) * pool_token_amount / App.globalGet(POOL_TOKENS_OUTSTANDING_KEY)) / Int(4) ),
            )),
    )

```

# On Swap

```python
def get_swap():
    token_txn_index = Txn.group_index() - Int(1)
    option = Txn.application_args[1]

    on_swap = Seq(
        Assert(
            validateTokenReceived(token_txn_index, TOKEN_FUNDING_KEY),
        ),
        If(option == Bytes("buy_yes"))
        .Then(
            Seq(
                mintAndSendYesToken(
                    Txn.sender(),
                    Gtxn[token_txn_index].asset_amount(),
                ),
                Approve()
            ),
        )
        .ElseIf(option == Bytes("buy_no"))
        .Then(
            Seq(
                mintAndSendNoToken(
                    Txn.sender(),
                    Gtxn[token_txn_index].asset_amount(),
                ),
                Approve()
            ),
        ),
        Reject()
        )

    return on_swap
```

The code runs when an account calls `Txn.application_args[0]` that equals to `Bytes("swap")` into the smart contract. It returns true if the token received by the smart contract is the same funding (reserve) token declared in `on_create` part of the program.

Depending on the argument in `Txn.application_args[1]`, the user either can choose a yes or no option token. The price of each token is explicitly determined by the existing liquidity, reserves of yes and no tokens and the size of the trade.

```python
def mintAndSendNoToken(
    receiver: TealType.bytes, amount: TealType.uint64
) -> Expr:
    funding = AssetHolding.balance(
        Global.current_application_address(), App.globalGet(TOKEN_FUNDING_KEY)
    )
    tokensOut: ScratchVar = ScratchVar(TealType.uint64)
    return Seq(
        tokensOut.store(
            App.globalGet(YES_TOKENS_RESERVES) * amount / (App.globalGet(NO_TOKENS_RESERVES) + amount )
        ),
        App.globalPut(NO_TOKENS_OUTSTANDING_KEY, App.globalGet(NO_TOKENS_OUTSTANDING_KEY) + tokensOut.load()),
        App.globalPut(NO_TOKENS_RESERVES, App.globalGet(NO_TOKENS_RESERVES) - tokensOut.load()),
        sendToken(NO_TOKEN_KEY, receiver, tokensOut.load()),
        If(App.globalGet(NO_TOKENS_OUTSTANDING_KEY) > App.globalGet(YES_TOKENS_OUTSTANDING_KEY))
        .Then(
            App.globalPut(TOKEN_FUNDING_RESERVES, App.globalGet(NO_TOKENS_OUTSTANDING_KEY) * Int(2))
        ),
        funding,
        App.globalPut(
            POOL_FUNDING_RESERVES,
            funding.value() - App.globalGet(TOKEN_FUNDING_RESERVES)
        ),
    )


def mintAndSendYesToken(
    receiver: TealType.bytes, amount: TealType.uint64
) -> Expr:
    funding = AssetHolding.balance(
        Global.current_application_address(), App.globalGet(TOKEN_FUNDING_KEY)
    )
    tokensOut: ScratchVar = ScratchVar(TealType.uint64)
    return Seq(
        tokensOut.store(
            (App.globalGet(NO_TOKENS_RESERVES) * amount / (App.globalGet(YES_TOKENS_RESERVES) + amount ))
        ),
        App.globalPut(YES_TOKENS_OUTSTANDING_KEY, App.globalGet(YES_TOKENS_OUTSTANDING_KEY) + tokensOut.load()),
        App.globalPut(YES_TOKENS_RESERVES, App.globalGet(YES_TOKENS_RESERVES) - tokensOut.load()),
        sendToken(YES_TOKEN_KEY, receiver, tokensOut.load()),
        If(App.globalGet(YES_TOKENS_OUTSTANDING_KEY) > App.globalGet(NO_TOKENS_OUTSTANDING_KEY))
        .Then(
            App.globalPut(TOKEN_FUNDING_RESERVES, App.globalGet(YES_TOKENS_OUTSTANDING_KEY) * Int(2))
        ),
        funding,
        App.globalPut(
            POOL_FUNDING_RESERVES,
            funding.value() - App.globalGet(TOKEN_FUNDING_RESERVES)
        ),
    )
```

# On Result

```python
def get_result():
    result = Txn.application_args[1]

    on_result = Seq(
        Assert(
            Txn.sender() == App.globalGet(CREATOR_KEY)
        ),
        If(result == Bytes("yes"))
        .Then(
            Seq(
                App.globalPut(RESULT, App.globalGet(YES_TOKEN_KEY)),
                Approve()
            )
        )
        .ElseIf(
                result == Bytes("no"),
            )
        .Then(
            Seq(
                App.globalPut(RESULT, App.globalGet(NO_TOKEN_KEY)),
                Approve()
            )
        ),
        Reject(),
    )

    return on_result
```

The code runs when an account calls `Txn.application_args[0]` that equals to `Bytes("result")` into the smart contract. It returns true if the token received by the smart contract is the creator account declared in `on_create` part of the program.

Depending on the argument in `Txn.application_args[1]`, the creator should choose a yes or no result of the event to declare the winning option.

# On Redemption

```python
def get_redemption():
    token_txn_index = Txn.group_index() - Int(1)

    on_redemption = Seq(
        Assert(
            And(
                validateTokenReceived(token_txn_index, RESULT),
            )
        ),
        redeemToken(
            Txn.sender(),
            Gtxn[token_txn_index].asset_amount(),
        ),
        Approve(),
    )

    return on_redemption
```

The code runs when an account calls `Txn.application_args[0]` that equals to `Bytes("redeem")` into the smart contract. It returns true if the token received by the smart contract is the winner decided in `on_result` part of the program.

`redeemToken` tracks the withdrawal of Yes/No Tokens. Since the initial distribution of liqudity provided was distribtued in 50%/50% towards each token, after the deadline the winning token should be worth double its initial price.

```python
def redeemToken(
    receiver: TealType.bytes,
    result_token_amount: TealType.uint64,
) -> Expr:

    return Seq(
        sendToken(
            TOKEN_FUNDING_KEY,
            receiver,
            result_token_amount * Int(2)
        ),
        App.globalPut(
            TOKEN_FUNDING_RESERVES, App.globalGet(TOKEN_FUNDING_RESERVES) - result_token_amount * Int(2)
        ),
        If( App.globalGet(RESULT) == App.globalGet(YES_TOKEN_KEY) )
        .Then(
            App.globalPut(
                YES_TOKENS_OUTSTANDING_KEY, App.globalGet(YES_TOKENS_OUTSTANDING_KEY) - result_token_amount
            ),
        )
        .ElseIf(App.globalGet(RESULT) == App.globalGet(NO_TOKEN_KEY) )
        .Then(
            App.globalPut(
                NO_TOKENS_OUTSTANDING_KEY, App.globalGet(NO_TOKENS_OUTSTANDING_KEY) - result_token_amount
            ),
        ),
    )
```

# Contract Demo

## Create Account

To deploy a smart contract we create an account and fund it using [Testnet Dispensary](https://dispenser.testnet.aws.algodev.network/).

```python
from algosdk import account

# generate an account
private_key, address = account.generate_account()
print("Private key:", private_key)
print("Address:", address)
```

## Connect to AlgodClient

We register on the [purestake.com](https://purestake.com) to obtain the api key and initialize the Algorand Client.

```python
algod_token = "Enter Yout token here"
algod_address = "https://testnet-algorand.api.purestake.io/ps2"

headers = {
   "X-API-Key": algod_token,
}

# initialize an algodClient
client = algod.AlgodClient(algod_token, algod_address, headers)
```

## Create Reserve Asset

We create an asset that will be used for reserves in the contract and return the asset index.

```python
from algosdk import account
from algosdk.future import transaction

def wait_for_confirmation(client, txid):
    last_round = client.status().get("last-round")
    txinfo = client.pending_transaction_info(txid)
    while not (txinfo.get("confirmed-round") and txinfo.get("confirmed-round") > 0):
        print("Waiting for confirmation...")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(txid)
    print(
        "Transaction {} confirmed in round {}.".format(
            txid, txinfo.get("confirmed-round")
        )
    )
    return txinfo


def create_asset(client, private_key):
    # declare sender
    sender = account.address_from_private_key(private_key)

    params = client.suggested_params()

    txn = transaction.AssetConfigTxn(
        sender=sender,
        sp=params,
        total=1_000_000_000,
        default_frozen=False,
        unit_name="Copio",
        asset_name="coin",
        manager=sender,
        reserve=sender,
        freeze=sender,
        clawback=sender,
        strict_empty_address_check=False,
        url=None,
        decimals=0)

    # Sign with secret key of creator
    stxn = txn.sign(private_key)

    # Send the transaction to the network and retrieve the txid.

    txid = client.send_transaction(stxn)
    print("Signed transaction with txID: {}".format(txid))
    # Wait for the transaction to be confirmed
    response = wait_for_confirmation(client, txid)
    print("TXID: ", txid)
    print("Result confirmed in round: {}".format(response['confirmed-round']))
    return response['asset-index']
```

## Deploy Contract

First, to interact with the smart contract we need to compile and deploy it. `createAmmApp` function requires client, reserve token id, minimum increment of the reserve token, creator address and private_key to sign the transaction.

```python
def waitForTransaction(
    client: AlgodClient, txID: str, timeout: int = 10
):

    lastStatus = client.status()
    lastRound = lastStatus["last-round"]
    startRound = lastRound

    while lastRound < startRound + timeout:
        pending_txn = client.pending_transaction_info(txID)

        if pending_txn.get("confirmed-round", 0) > 0:
            return pending_txn

        if pending_txn["pool-error"]:
            raise Exception("Pool error: {}".format(pending_txn["pool-error"]))

        lastStatus = client.status_after_block(lastRound + 1)

        lastRound += 1

    raise Exception(
        "Transaction {} not confirmed after {} rounds".format(txID, timeout)
    )

def fullyCompileContract(
    client: AlgodClient, contract: Expr
) -> bytes:

    teal = compileTeal(contract, mode=Mode.Application, version=6)
    response = client.compile(teal)

    return b64decode(response["result"])

def getContracts(client: AlgodClient) -> Tuple[bytes, bytes]:
    """Get the compiled TEAL contracts for the amm.
    Args:q
        client: An algod client that has the ability to compile TEAL programs.
    Returns:
        A tuple of 2 byte strings. The first is the approval program, and the
        second is the clear state program.
    """

    APPROVAL_PROGRAM = fullyCompileContract(client, approval_program())
    CLEAR_STATE_PROGRAM = fullyCompileContract(client, clear_program())

    return APPROVAL_PROGRAM, CLEAR_STATE_PROGRAM

def createAmmApp(
    client: AlgodClient,
    token: int,
    minIncrement: int,
    creator: str,
    private_key: str
) -> int:
    """Creates a new amm.
    Args:
        client: An algod client.
        creator: The account that will create the amm application.
        token: The id of token A in the liquidity pool,
    Returns:
        The ID of the newly created amm app.
    """
    approval, clear = getContracts(client)

    globalSchema = transaction.StateSchema(num_uints=13, num_byte_slices=1)
    localSchema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

    app_args = [
        encoding.decode_address(creator),
        token.to_bytes(8, "big"),
        minIncrement.to_bytes(8, "big"),
    ]

    txn = transaction.ApplicationCreateTxn(
        sender=creator,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval,
        clear_program=clear,
        global_schema=globalSchema,
        local_schema=localSchema,
        app_args=app_args,
        sp=client.suggested_params(),
    )

    signedTxn = txn.sign(private_key)

    client.send_transaction(signedTxn)

    response = waitForTransaction(client, signedTxn.get_txid())
    assert response["application-index"] is not None and response["application-index"] > 0
    return response["application-index"]
```

## Setting up the AMM

```python
MIN_BALANCE_REQUIREMENT = (
    # min account balance
    110_000
    # additional min balance for 4 assets
    + 100_000 * 4
)


def setupAmmApp(
    client: AlgodClient,
    appID: int,
    token: int,
    funder: str,
    private_key: str
) -> int:
    """Finish setting up an amm.
    This operation funds the pool account, creates pool token,
    and opts app into tokens A and B, all in one atomic transaction group.
    Args:
        client: An algod client.
        appID: The app ID of the amm.
        funder: The account providing the funding for the escrow account.
        token: Token id.
        private_key
    Return: pool token id
    """
    appAddr = get_application_address(appID)

    suggestedParams = client.suggested_params()

    fundAppTxn = transaction.PaymentTxn(
        sender=funder,
        receiver=appAddr,
        amt=MIN_BALANCE_REQUIREMENT,
        sp=suggestedParams,
    )

    setupTxn = transaction.ApplicationCallTxn(
        sender=funder,
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"setup"],
        foreign_assets=[token],
        sp=suggestedParams,
    )

    transaction.assign_group_id([fundAppTxn, setupTxn])

    signedFundAppTxn = fundAppTxn.sign(private_key)
    signedSetupTxn = setupTxn.sign(private_key)

    client.send_transactions([signedFundAppTxn, signedSetupTxn])

    waitForTransaction(client, signedFundAppTxn.get_txid())
    glob_state = client.application_info(appID)['params']['global-state']

    ids = {}

    for i in range(len(glob_state)):
        if b64decode(glob_state[i]['key']) == b"pool_token_key":
            ids['pool_token_key'] = glob_state[i]['value']['uint']
        elif b64decode(glob_state[i]['key']) == b"yes_token_key":
            ids['yes_token_key'] = glob_state[i]['value']['uint']
        elif b64decode(glob_state[i]['key']) == b"no_token_key":
            ids['no_token_key'] = glob_state[i]['value']['uint']

    return ids
```

`setupAmmApp` method requires an `appID` as one of the arguments. It funds the app and calls the smart contract with the given arguments all in one atomic transaction group. The method returns the dictionary with ids of created pool and option tokens.

Further we need to opt in to the created new assets:

```python
def optInToPoolToken(
    client: AlgodClient,
    poolToken: int,
    account: str,
    private_key: str
) -> None:
    """Opts into Pool Token
    Args:
        client: An algod client.
        account: The account opting into the token.
        poolToken: Token id.
        private_key: to sign the tx.
    """
    suggestedParams = client.suggested_params()

    optInTxn = transaction.AssetOptInTxn(
        sender=account, index=poolToken, sp=suggestedParams
    )

    signedOptInTxn = optInTxn.sign(private_key)

    client.send_transaction(signedOptInTxn)
    waitForTransaction(client, signedOptInTxn.get_txid())
```

## Supplying AMM with Liqudity

```python
def supply(
    client: AlgodClient, appID: int, q: int, supplier: str, private_key: str, \
    token: int, poolToken: int, yesToken: int, noToken: int
) -> None:
    """Supply liquidity to the pool.
    """
    appAddr = get_application_address(appID)
    suggestedParams = client.suggested_params()

    # pay for the fee incurred by AMM for sending back the pool token
    feeTxn = transaction.PaymentTxn(
        sender=supplier,
        receiver=appAddr,
        amt=MIN_BALANCE_REQUIREMENT,
        sp=suggestedParams,
    )

    tokenTxn = transaction.AssetTransferTxn(
        sender=supplier,
        receiver=appAddr,
        index=token,
        amt=q,
        sp=suggestedParams,
    )

    appCallTxn = transaction.ApplicationCallTxn(
        sender=supplier,
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"supply"],
        foreign_assets=[token, poolToken, yesToken, noToken],
        sp=suggestedParams,
    )

    transaction.assign_group_id([feeTxn, tokenTxn, appCallTxn])
    signedFeeTxn = feeTxn.sign(private_key)
    signedTokenTxn = tokenTxn.sign(private_key)
    signedAppCallTxn = appCallTxn.sign(private_key)

    client.send_transactions(
        [signedFeeTxn, signedTokenTxn, signedAppCallTxn]
    )
    waitForTransaction(client, signedAppCallTxn.get_txid())
```

## Swap stablecoin for Option

```python
def swap(
    client: AlgodClient,
    appID: int,
    option: str,
    q: int,
    supplier: int,
    private_key: str,
    token: int,
    poolToken: int,
    yesToken: int,
    noToken: int
) -> None:

    if option == 'yes':
        second_argument = b"buy_yes"
    elif option =='no':
        second_argument = b"buy_no"
    else:
        return

    appAddr = get_application_address(appID)
    suggestedParams = client.suggested_params()

    # pay for the fee incurred by AMM for sending back the pool token
    feeTxn = transaction.PaymentTxn(
        sender=supplier,
        receiver=appAddr,
        amt=2_000,
        sp=suggestedParams,
    )

    tokenTxn = transaction.AssetTransferTxn(
        sender=supplier,
        receiver=appAddr,
        index=token,
        amt=q,
        sp=suggestedParams,
    )

    appCallTxn = transaction.ApplicationCallTxn(
        sender=supplier,
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[ b"swap", second_argument],
        foreign_assets=[token, poolToken, yesToken, noToken],
        sp=suggestedParams,
    )

    transaction.assign_group_id([feeTxn, tokenTxn, appCallTxn])
    signedFeeTxn = feeTxn.sign(private_key)
    signedTokenTxn = tokenTxn.sign(private_key)
    signedAppCallTxn = appCallTxn.sign(private_key)

    client.send_transactions(
        [signedFeeTxn, signedTokenTxn, signedAppCallTxn]
    )
    waitForTransaction(client, signedAppCallTxn.get_txid())
```

## Withdraw LP tokens

```python

def withdraw(
    client: AlgodClient,
    appID: int,
    poolToken: int,
    poolTokenAmount: int,
    withdrawAccount: str,
    token: int,
    private_key: str
) -> None:
    """Withdraw liquidity  + rewards from the pool back to supplier.
    Supplier should receive stablecoin + fees proportional to the liquidity share in the pool they choose to withdraw.
    """
    appAddr = get_application_address(appID)
    suggestedParams = client.suggested_params()

    # pay for the fee incurred by AMM for sending back tokens A and B
    feeTxn = transaction.PaymentTxn(
        sender=withdrawAccount,
        receiver=appAddr,
        amt=2_000,
        sp=suggestedParams,
    )


    poolTokenTxn = transaction.AssetTransferTxn(
        sender=withdrawAccount,
        receiver=appAddr,
        index=poolToken,
        amt=poolTokenAmount,
        sp=suggestedParams,
    )

    appCallTxn = transaction.ApplicationCallTxn(
        sender=withdrawAccount,
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"withdraw"],
        foreign_assets=[token, poolToken],
        sp=suggestedParams,
    )

    transaction.assign_group_id([feeTxn, poolTokenTxn, appCallTxn])
    signedFeeTxn = feeTxn.sign(private_key)
    signedPoolTokenTxn = poolTokenTxn.sign(private_key)
    signedAppCallTxn = appCallTxn.sign(private_key)

    client.send_transactions([signedFeeTxn, signedPoolTokenTxn, signedAppCallTxn])
    waitForTransaction(client, signedAppCallTxn.get_txid())
```

## Set result

```python
def set_result(
    client: AlgodClient,
    appID: int,
    funder: str,
    private_key: str,
    second_argument
):
    """ Set the winning token key
    """
    appAddr = get_application_address(appID)

    suggestedParams = client.suggested_params()

    feeTxn = transaction.PaymentTxn(
        sender=funder,
        receiver=appAddr,
        amt=2_000,
        sp=suggestedParams,
    )

    callTxn = transaction.ApplicationCallTxn(
        sender=funder,
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"result", second_argument],
        sp=suggestedParams,
    )

    transaction.assign_group_id([feeTxn, callTxn])
    signedFeeTxn = feeTxn.sign(private_key)
    signedAppCallTxn = callTxn.sign(private_key)

    client.send_transactions([signedFeeTxn, signedAppCallTxn])
    waitForTransaction(client, signedAppCallTxn.get_txid())
```

## Redeem Resolved Option for Stablecoin

```python
def redeem(
    client: AlgodClient, appID: int, Token:int, TokenAmount: int,
    withdrawAccount: str, token: int, private_key: str
) -> None:

    appAddr = get_application_address(appID)
    suggestedParams = client.suggested_params()

    # pay for the fee incurred by AMM for sending back tokens A and B
    feeTxn = transaction.PaymentTxn(
        sender=withdrawAccount,
        receiver=appAddr,
        amt=2_000,
        sp=suggestedParams,
    )


    TokenTxn = transaction.AssetTransferTxn(
        sender=withdrawAccount,
        receiver=appAddr,
        index=Token,
        amt=TokenAmount,
        sp=suggestedParams,
    )

    appCallTxn = transaction.ApplicationCallTxn(
        sender=withdrawAccount,
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"redeem"],
        foreign_assets=[token, Token],
        sp=suggestedParams,
    )

    transaction.assign_group_id([feeTxn, TokenTxn, appCallTxn])
    signedFeeTxn = feeTxn.sign(private_key)
    signedPoolTokenTxn = TokenTxn.sign(private_key)
    signedAppCallTxn = appCallTxn.sign(private_key)

    client.send_transactions([signedFeeTxn, signedPoolTokenTxn, signedAppCallTxn])
    waitForTransaction(client, signedAppCallTxn.get_txid())
```

## Close out the AMM

```python
def closeAmm(
    client: AlgodClient, appID: int, closer: str, private_key: str
)-> None:
    """Close an AMM.
    Args:
        client: An Algod client.
        appID: The app ID of the amm.
        closer: closer account public address. Must be the original creator of the pool.
        private_key: closer account private key to sign the transactions.
    """

    deleteTxn = transaction.ApplicationDeleteTxn(
        sender=closer,
        index=appID,
        sp=client.suggested_params(),
    )
    signedDeleteTxn = deleteTxn.sign(private_key)

    client.send_transaction(signedDeleteTxn)

    waitForTransaction(client, signedDeleteTxn.get_txid())
```

## Example Script

```python
import os
from dotenv import load_dotenv
from algosdk import account
from algosdk.v2client import algod

from create_asset import create_asset
from amm_api import createAmmApp, setupAmmApp, optInToPoolToken, \
    supply, withdraw, swap, set_result, closeAmm, redeem


load_dotenv()

private_key = os.getenv('key')
creator = account.address_from_private_key(private_key)

algod_token = os.getenv('algod_token')

algod_address = "https://testnet-algorand.api.purestake.io/ps2"

headers = {
   "X-API-Key": algod_token,
}

# initialize an algodClient
client = algod.AlgodClient(algod_token, algod_address, headers)

# create (stable) asset
token = create_asset(client, private_key)

appID = createAmmApp(
    client=client,
    creator=creator,
    private_key=private_key,
    token=token,
    minIncrement=1000,
)

print(f"Alice is setting up and funding amm {appID}")

Tokens = setupAmmApp(
    client=client,
    appID=appID,
    funder=creator,
    private_key=private_key,
    token=token,
)

poolToken = Tokens['pool_token_key']
yesToken = Tokens['yes_token_key']
noToken = Tokens['no_token_key']

print(Tokens['pool_token_key'], Tokens['yes_token_key'], Tokens['no_token_key'])

optInToPoolToken(client, creator, private_key, poolToken)
optInToPoolToken(client, creator, private_key, yesToken)
optInToPoolToken(client, creator, private_key, noToken)


print("Supplying AMM with initial token")

poolTokenFirstAmount = 500_000

supply(
    client=client,
    appID=appID,
    q=poolTokenFirstAmount,
    supplier=creator,
    private_key=private_key,
    token=token,
    poolToken=poolToken,
    yesToken=yesToken, noToken=noToken
)

print("Supplying AMM with more tokens")

poolTokenSecondAmount = 1_500_000

supply(
    client=client,
    appID=appID,
    q=poolTokenSecondAmount,
    supplier=creator,
    private_key=private_key,
    token=token,
    poolToken=poolToken,
    yesToken=yesToken, noToken=noToken
)

print("Swapping")

yesTokenAmount = 100_000

# buy yes token
swap(
    client=client,
    appID=appID,
    option="yes",
    q=yesTokenAmount,
    supplier=creator,
    private_key=private_key,
    token=token,
    poolToken=poolToken,
    yesToken=yesToken,
    noToken=noToken
)

#buy no token
swap(
    client=client,
    appID=appID,
    option="no",
    q=yesTokenAmount,
    supplier=creator,
    private_key=private_key,
    token=token,
    poolToken=poolToken,
    yesToken=yesToken,
    noToken=noToken
)

print("Withdrawing")

AllTokens = 2_000_000

withdraw(
    client = client,
    appID = appID,
    poolTokenAmount = AllTokens,
    poolToken = poolToken,
    withdrawAccount = creator,
    private_key = private_key,
    token = token
)

print("Result")
#set winner

set_result(
    client = client,
    appID = appID,
    second_argument=b"yes",
    funder=creator,
    private_key = private_key
)


# redemption for for yes/no

print("Redeeming")

YesTokensAmount = 95_238

redeem(
    client = client,
    appID = appID,
    TokenAmount = YesTokensAmount,
    Token = yesToken,
    withdrawAccount = creator,
    private_key = private_key,
    token = token
)

# Delete

print("Deleting")

closeAmm(
    client = client,
    appID = appID,
    closer=creator,
    private_key = private_key
)
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
