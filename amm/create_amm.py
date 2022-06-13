from typing import List, Tuple, Dict, Any, Optional, Union
from base64 import b64decode

from algosdk.v2client.algod import AlgodClient
from algosdk import encoding
from algosdk.future import transaction
from algosdk.logic import get_application_address

from pyteal import compileTeal, Mode, Expr

from contracts.amm import approval_program, clear_program

#https://github.com/Pfed-prog/AlgoSwapper/blob/main/Voting/start.py

MIN_BALANCE_REQUIREMENT = (
    # min account balance
    100_000
    # additional min balance for 3 assets
    + 100_000 * 3
)

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


def fullyCompileContract(client: AlgodClient, contract: Expr) -> bytes:
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
    tokenA: int,
    tokenB: int,
    feeBps: int,
    minIncrement: int,
    creator, private_key
) -> int:
    """Create a new amm.
    Args:
        client: An algod client.
        creator: The account that will create the amm application.
        tokenA: The id of token A in the liquidity pool,
        tokenB: The id of token B in the liquidity pool,
        feeBps: The basis point fee to be charged per swap
    Returns:
        The ID of the newly created amm app.
    """
    approval, clear = getContracts(client)

    # tokenA, tokenB, poolToken, fee
    globalSchema = transaction.StateSchema(num_uints=7, num_byte_slices=1)
    localSchema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

    app_args = [
        encoding.decode_address(creator),
        tokenA.to_bytes(8, "big"),
        tokenB.to_bytes(8, "big"),
        feeBps.to_bytes(8, "big"),
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


def setupAmmApp(
    client: AlgodClient,
    appID: int,
    tokenA: int,
    tokenB: int,
    funder, private_key
) -> int:
    """Finish setting up an amm.
    This operation funds the pool account, creates pool token,
    and opts app into tokens A and B, all in one atomic transaction group.
    Args:
        client: An algod client.
        appID: The app ID of the amm.
        funder: The account providing the funding for the escrow account.
        tokenA: Token A id.
        tokenB: Token B id.
    Return: pool token id
    """
    appAddr = get_application_address(appID)

    suggestedParams = client.suggested_params()

    fundingAmount = (
        MIN_BALANCE_REQUIREMENT
        # additional balance to create pool token and opt into tokens A and B
        + 1_000 * 3
    )

    fundAppTxn = transaction.PaymentTxn(
        sender=funder,
        receiver=appAddr,
        amt=fundingAmount,
        sp=suggestedParams,
    )

    setupTxn = transaction.ApplicationCallTxn(
        sender=funder,
        index=appID,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"setup"],
        foreign_assets=[tokenA, tokenB],
        sp=suggestedParams,
    )

    transaction.assign_group_id([fundAppTxn, setupTxn])

    signedFundAppTxn = fundAppTxn.sign(private_key)
    signedSetupTxn = setupTxn.sign(private_key)

    client.send_transactions([signedFundAppTxn, signedSetupTxn])

    waitForTransaction(client, signedFundAppTxn.get_txid())

    glob_state = client.application_info(app)['params']['global-state']


    for i in range(len(glob_state)):
        if b64decode(glob_state[i]['key']) == b"pool_token_key":
            return glob_state[i]['value']['uint']
