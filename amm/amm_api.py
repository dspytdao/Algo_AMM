from email.headerregistry import Address
from typing import Tuple 
from base64 import b64decode

from pyteal import compileTeal, Mode, Expr

from algosdk.v2client.algod import AlgodClient
from algosdk import encoding
from algosdk.future import transaction
from algosdk.logic import get_application_address

from contracts.amm import approval_program, clear_program

MIN_BALANCE_REQUIREMENT = (
    # min account balance
    110_000
    # additional min balance for 4 assets
    + 100_000 * 4
    #0.51
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
    token: int,
    minIncrement: int,
    creator, private_key
) -> int:
    """Create a new amm.
    Args:
        client: An algod client.
        creator: The account that will create the amm application.
        token: The id of token A in the liquidity pool,
    Returns:
        The ID of the newly created amm app.
    """
    approval, clear = getContracts(client)

    # tokenA, tokenB, poolToken, fee
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


def setupAmmApp(
    client: AlgodClient,
    appID: int,
    token: int,
    funder, private_key
) -> int:
    """Finish setting up an amm.
    This operation funds the pool account, creates pool token,
    and opts app into tokens A and B, all in one atomic transaction group.
    Args:
        client: An algod client.
        appID: The app ID of the amm.
        funder: The account providing the funding for the escrow account.
        token: Token id.
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


def optInToPoolToken(client, account, private_key, poolToken):
    suggestedParams = client.suggested_params()

    optInTxn = transaction.AssetOptInTxn(
        sender=account, index=poolToken, sp=suggestedParams
    )

    signedOptInTxn = optInTxn.sign(private_key)

    client.send_transaction(signedOptInTxn)
    waitForTransaction(client, signedOptInTxn.get_txid())


def supply(
    client: AlgodClient, appID: int, q: int, supplier, private_key, \
    token, poolToken, yesToken, noToken
) -> None:
    """Supply liquidity to the pool.
    Let rA, rB denote the existing pool reserves of token A and token B respectively
    First supplier will receive sqrt(qA*qB) tokens, subsequent suppliers will receive
    qA/rA where rA is the amount of token A already in the pool.
    If qA/qB != rA/rB, the pool will first attempt to take full amount qA, returning excess token B
    Else if there is insufficient amount qB, the pool will then attempt to take the full amount qB, returning
     excess token A
    Else transaction will be rejected
    Args:
        client: AlgodClient,
        appID: amm app id,
        q: amount of token to supply the pool
        supplier: supplier account
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


def swap(client: AlgodClient, appID: int, option: str, q: int, supplier, \
    private_key, token, poolToken, yesToken, noToken):

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


def withdraw(
    client: AlgodClient, appID: int, poolToken:int, poolTokenAmount: int, withdrawAccount, token, private_key
) -> None:
    """Withdraw liquidity  + rewards from the pool back to supplier.
    Supplier should receive stablecoin + fees proportional to the liquidity share in the pool they choose to withdraw.
    Args:
        client: AlgodClient,
        appID: amm app id,
        poolTokenAmount: pool token quantity,
        withdrawAccount: supplier account,
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


def redeem(
    client: AlgodClient, appID: int, Token:int, TokenAmount: int, withdrawAccount, token, private_key
) -> None:
    """
    Withdraw liquidity  + rewards from the pool back to supplier.
    Supplier should receive stablecoin + fees proportional to the liquidity share in the pool they choose to withdraw.
    Args:
        client: AlgodClient,
        appID: amm app id,
        poolTokenAmount: pool token quantity,
        withdrawAccount: supplier account,
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


def set_result(
    client: AlgodClient,
    appID: int,
    second_argument,
    funder, private_key):    
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


def closeAmm(client: AlgodClient, appID: int, closer, private_key):
    """Close an amm.
    Args:
        client: An Algod client.
        appID: The app ID of the amm.
        closer: closer account. Must be the original creator of the pool.
    """

    deleteTxn = transaction.ApplicationDeleteTxn(
        sender=closer,
        index=appID,
        sp=client.suggested_params(),
    )
    signedDeleteTxn = deleteTxn.sign(private_key)

    client.send_transaction(signedDeleteTxn)

    waitForTransaction(client, signedDeleteTxn.get_txid())