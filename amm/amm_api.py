"""this file is to connect to the contract"""
import json
from typing import Tuple
from base64 import b64decode

from pyteal import compileTeal, Mode, Expr

from algosdk.v2client.algod import AlgodClient
from algosdk import encoding
from algosdk.future import transaction
from algosdk.logic import get_application_address

from amm.contracts.amm import approval_program, clear_program

MIN_BALANCE_REQUIREMENT = (
    # min account balance
    110_000
    # additional min balance for 4 assets
    + 100_000 * 4
)


def wait_for_transaction(
    client: AlgodClient, tx_id: str, timeout: int = 10
) -> json:
    """monitors tx
    """

    last_status = client.status()
    last_round = last_status["last-round"]
    start_round= last_round

    while last_round < start_round + timeout:
        pending_txn = client.pending_transaction_info(tx_id)

        if pending_txn.get("confirmed-round", 0) > 0:
            return pending_txn

        if pending_txn["pool-error"]:
            raise Exception("Pool error:")

        last_status= client.status_after_block(last_round + 1)

        last_round += 1

    raise Exception(
        f"Transaction {tx_id} not confirmed after {timeout} rounds"
    )


def fully_compile_contract(
    client: AlgodClient, contract: Expr
) -> bytes:
    """compiles teal
    """
    teal = compileTeal(contract, mode=Mode.Application, version=6)
    response = client.compile(teal)

    return b64decode(response["result"])


def get_contracts(client: AlgodClient) -> Tuple[bytes, bytes]:
    """Get the compiled TEAL contracts for the amm.
    Args:q
        client: An algod client that has the ability to compile TEAL programs.
    Returns:
        A tuple of 2 byte strings. The first is the approval program, and the
        second is the clear state program.
    """

    approval_progra_compiled = fully_compile_contract(client, approval_program())
    clear_state_program_compiled = fully_compile_contract(client, clear_program())

    return approval_progra_compiled, clear_state_program_compiled


def create_amm_app(
    client: AlgodClient,
    token: int,
    min_increment: int,
    creator: str, private_key: str
) -> int:
    """Creates a new amm.
    Args:
        client: An algod client.
        creator: The account that will create the amm application.
        token: The id of token A in the liquidity pool,
        min_increment: int that
        private_key to sign the tx
    Returns:
        The ID of the newly created amm app.
    """
    approval, clear = get_contracts(client)

    global_schema = transaction.StateSchema(num_uints=13, num_byte_slices=1)
    local_schema = transaction.StateSchema(num_uints=0, num_byte_slices=0)

    app_args = [
        encoding.decode_address(creator),
        token.to_bytes(8, "big"),
        min_increment.to_bytes(8, "big"),
    ]

    txn = transaction.ApplicationCreateTxn(
        sender=creator,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval,
        clear_program=clear,
        global_schema=global_schema,
        local_schema=local_schema,
        app_args=app_args,
        sp=client.suggested_params(),
    )

    signed_tx = txn.sign(private_key)

    client.send_transaction(signed_tx)

    response = wait_for_transaction(client, signed_tx.get_txid())
    assert response["application-index"] is not None and response["application-index"] > 0
    return response["application-index"]


def setup_amm_app(
    client: AlgodClient,
    app_id: int,
    token: int,
    funder: str, private_key: str
) -> int:
    """Finish setting up an amm.
    This operation funds the pool account, creates pool token,
    and opts app into tokens A and B, all in one atomic transaction group.
    Args:
        client: An algod client.
        app_id: The app ID of the amm.
        funder: The account providing the funding for the escrow account.
        token: Token id.
        private_key to sign the tx
    Return: pool token id
    """
    app_addr = get_application_address(app_id)

    suggested_params = client.suggested_params()

    fund_app_tx = transaction.PaymentTxn(
        sender=funder,
        receiver=app_addr,
        amt=MIN_BALANCE_REQUIREMENT,
        sp=suggested_params,
    )

    setup_tx = transaction.ApplicationCallTxn(
        sender=funder,
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"setup"],
        foreign_assets=[token],
        sp=suggested_params,
    )

    transaction.assign_group_id([fund_app_tx, setup_tx])

    signed_fund_spp_txn = fund_app_tx.sign(private_key)
    signed_setup_tx = setup_tx.sign(private_key)

    client.send_transactions([signed_fund_spp_txn, signed_setup_tx])

    wait_for_transaction(client, signed_fund_spp_txn.get_txid())
    glob_state = client.application_info(app_id)['params']['global-state']

    ids = {}

    for i, _ in enumerate(glob_state):
        if b64decode(glob_state[i]['key']) == b"pool_token_key":
            ids['pool_token_key'] = glob_state[i]['value']['uint']
        elif b64decode(glob_state[i]['key']) == b"yes_token_key":
            ids['yes_token_key'] = glob_state[i]['value']['uint']
        elif b64decode(glob_state[i]['key']) == b"no_token_key":
            ids['no_token_key'] = glob_state[i]['value']['uint']

    return ids


def opt_in_to_pool_token(
    client: AlgodClient,
    account: str,
    private_key: str,
    pool_token: int,
) -> None:
    """Opts into Pool Token
    Args:
        client: An algod client.
        account: The account opting into the token.
        private_key: to sign the tx.
        pool_token: Token id.
    """
    suggested_params = client.suggested_params()

    optin_tx = transaction.AssetOptInTxn(
        sender=account, index=pool_token, sp=suggested_params
    )

    signed_opt_in_tx = optin_tx.sign(private_key)

    client.send_transaction(signed_opt_in_tx)
    wait_for_transaction(client, signed_opt_in_tx.get_txid())


def supply(
    client: AlgodClient, app_id: int, quantity: int, supplier: str, private_key: str, \
    token: int, pool_token: int, yes_token: int, no_token:int
) -> None:
    """Supply liquidity to the pool.
    """
    app_addr = get_application_address(app_id)
    suggested_params = client.suggested_params()

    # pay for the fee incurred by AMM for sending back the pool token
    fee_tx = transaction.PaymentTxn(
        sender=supplier,
        receiver=app_addr,
        amt=MIN_BALANCE_REQUIREMENT,
        sp=suggested_params,
    )

    token_tx = transaction.AssetTransferTxn(
        sender=supplier,
        receiver=app_addr,
        index=token,
        amt=quantity,
        sp=suggested_params,
    )

    app_call_tx = transaction.ApplicationCallTxn(
        sender=supplier,
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"supply"],
        foreign_assets=[token, pool_token, yes_token, no_token],
        sp=suggested_params,
    )

    transaction.assign_group_id([fee_tx, token_tx, app_call_tx])
    signed_fee_tx = fee_tx.sign(private_key)
    signedtoken_tx = token_tx.sign(private_key)
    signed_app_call_tx = app_call_tx.sign(private_key)

    client.send_transactions(
        [signed_fee_tx, signedtoken_tx, signed_app_call_tx]
    )
    wait_for_transaction(client, signed_app_call_tx.get_txid())


def swap(
    client: AlgodClient, app_id: int, option: str, quantity: int, supplier: int, \
    private_key: str, token: int, pool_token: int, yes_token: int, no_token: int
) -> None:
    """swap stbl for option
    """
    if option == 'yes':
        second_argument = b"buy_yes"
    elif option =='no':
        second_argument = b"buy_no"
    else:
        return

    app_addr = get_application_address(app_id)
    suggested_params = client.suggested_params()

    fee_tx = transaction.PaymentTxn(
        sender=supplier,
        receiver=app_addr,
        amt=2_000,
        sp=suggested_params,
    )

    token_tx = transaction.AssetTransferTxn(
        sender=supplier,
        receiver=app_addr,
        index=token,
        amt=quantity,
        sp=suggested_params,
    )

    app_call_tx = transaction.ApplicationCallTxn(
        sender=supplier,
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[ b"swap", second_argument],
        foreign_assets=[token, pool_token, yes_token, no_token],
        sp=suggested_params,
    )

    transaction.assign_group_id([fee_tx, token_tx, app_call_tx])
    signed_fee_tx = fee_tx.sign(private_key)
    signedtoken_tx = token_tx.sign(private_key)
    signed_app_call_tx = app_call_tx.sign(private_key)

    client.send_transactions(
        [signed_fee_tx, signedtoken_tx, signed_app_call_tx]
    )
    wait_for_transaction(client, signed_app_call_tx.get_txid())


def withdraw(
    client: AlgodClient, app_id: int, pool_token: int, pool_token_amount: int,
    withdrawal_account: str, token: int, private_key: str
) -> None:
    """Withdraw liquidity  + rewards from the pool back to supplier.
    Supplier should receive stablecoin + fees proportional
    to the liquidity share in the pool they choose to withdraw.
    """
    app_addr = get_application_address(app_id)
    suggested_params = client.suggested_params()

    # pay for the fee incurred by AMM for sending back tokens A and B
    fee_tx = transaction.PaymentTxn(
        sender=withdrawal_account,
        receiver=app_addr,
        amt=2_000,
        sp=suggested_params,
    )


    pool_token_tx = transaction.AssetTransferTxn(
        sender=withdrawal_account,
        receiver=app_addr,
        index=pool_token,
        amt=pool_token_amount,
        sp=suggested_params,
    )

    app_call_tx = transaction.ApplicationCallTxn(
        sender=withdrawal_account,
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"withdraw"],
        foreign_assets=[token, pool_token],
        sp=suggested_params,
    )

    transaction.assign_group_id([fee_tx, pool_token_tx, app_call_tx])
    signed_fee_tx = fee_tx.sign(private_key)
    signed_token_tx = pool_token_tx.sign(private_key)
    signed_app_call_tx = app_call_tx.sign(private_key)

    client.send_transactions([signed_fee_tx, signed_token_tx, signed_app_call_tx])
    wait_for_transaction(client, signed_app_call_tx.get_txid())


def redeem(
    client: AlgodClient, app_id: int, token_in: int, token_amount: int,
    withdrawal_account: str, token_out: int, private_key: str
) -> None:
    """reedems """

    app_addr = get_application_address(app_id)
    suggested_params = client.suggested_params()

    # pay for the fee incurred by AMM for sending back tokens A and B
    fee_tx = transaction.PaymentTxn(
        sender=withdrawal_account,
        receiver=app_addr,
        amt=2_000,
        sp=suggested_params,
    )


    token_tx = transaction.AssetTransferTxn(
        sender=withdrawal_account,
        receiver=app_addr,
        index=token_in,
        amt=token_amount,
        sp=suggested_params,
    )

    app_call_tx = transaction.ApplicationCallTxn(
        sender=withdrawal_account,
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"redeem"],
        foreign_assets=[token_out, token_in],
        sp=suggested_params,
    )

    transaction.assign_group_id([fee_tx, token_tx, app_call_tx])
    signed_fee_tx = fee_tx.sign(private_key)
    signed_token_tx = token_tx.sign(private_key)
    signed_app_call_tx = app_call_tx.sign(private_key)

    client.send_transactions([signed_fee_tx, signed_token_tx, signed_app_call_tx])
    wait_for_transaction(client, signed_app_call_tx.get_txid())


def set_result(
    client: AlgodClient,
    app_id: int,
    funder: str,
    private_key: str,
    second_argument
)-> None:
    """ sets result of the event
    """

    app_addr = get_application_address(app_id)

    suggested_params = client.suggested_params()

    fee_tx = transaction.PaymentTxn(
        sender=funder,
        receiver=app_addr,
        amt=2_000,
        sp=suggested_params,
    )

    call_tx = transaction.ApplicationCallTxn(
        sender=funder,
        index=app_id,
        on_complete=transaction.OnComplete.NoOpOC,
        app_args=[b"result", second_argument],
        sp=suggested_params,
    )

    transaction.assign_group_id([fee_tx, call_tx])
    signed_fee_tx = fee_tx.sign(private_key)
    signed_app_call_tx = call_tx.sign(private_key)

    client.send_transactions([signed_fee_tx, signed_app_call_tx])
    wait_for_transaction(client, signed_app_call_tx.get_txid())


def close_amm(
    client: AlgodClient,
    app_id: int,
    closer: str,
    private_key: str
)-> None:
    """Close an AMM.
    Args:
        client: An Algod client.
        app_id: The app ID of the amm.
        closer: closer account public address. Must be the original creator of the pool.
        private_key: closer account private key to sign the transactions.
    """

    delete_tx = transaction.ApplicationDeleteTxn(
        sender=closer,
        index=app_id,
        sp=client.suggested_params(),
    )
    signed_tx = delete_tx.sign(private_key)

    client.send_transaction(signed_tx)

    wait_for_transaction(client, signed_tx.get_txid())
