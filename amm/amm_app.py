"""api to the contract"""
from typing import Tuple
from base64 import b64decode

from pyteal import compileTeal, Mode, Expr
from algosdk import encoding
from algosdk.transaction import (StateSchema, ApplicationCreateTxn,
                                 OnComplete, PaymentTxn, ApplicationCallTxn, assign_group_id,
                                 AssetOptInTxn, AssetTransferTxn, ApplicationDeleteTxn)
from algosdk.v2client.algod import AlgodClient
from algosdk.logic import get_application_address

from amm.utils.account import Account
from amm.contracts.amm import approval_program, clear_program

MIN_BALANCE_REQUIREMENT = (
    # min account balance
    110_000
    # additional min balance for 4 assets
    + 100_000 * 4
)


def fully_compile_contract(
    client: AlgodClient, contract: Expr
) -> bytes:
    """
    Compiles teal.
    Args:
        client: algorand client
        contract: teal contract
    Returns: bytecode
    """
    teal = compileTeal(contract, mode=Mode.Application, version=6)
    response = client.compile(teal)

    return b64decode(response["result"])


def get_contracts(client: AlgodClient) -> Tuple[bytes, bytes]:
    """
    Get the compiled TEAL contracts for the AMM.
    Args:
        client: An algod client that has the ability to compile TEAL programs.
    Returns:
        The approval program and the clear state program.
    """

    approval_program_compiled = fully_compile_contract(
        client, approval_program())
    clear_state_program_compiled = fully_compile_contract(
        client, clear_program())

    return approval_program_compiled, clear_state_program_compiled


class App:
    """ Algorand App """

    def __init__(self, client: AlgodClient, app_id=0):
        self.client = client
        self.app_id = app_id
        self.app_addr = get_application_address(app_id)
        self.stable_token: int
        self.pool_token: int
        self.yes_token: int
        self.no_token: int

    def update_app_address(self):
        """
        Updates app address.
        """
        self.app_addr = get_application_address(self.app_id)

    def wait_for_transaction(
        self, tx_id: str, timeout: int = 10
    ):
        """
        Monitors transaction completion.
        Args:
            tx_id: transaction id
            timeout: timeout in rounds
        """

        last_status = self.client.status()
        last_round = last_status["last-round"]
        start_round = last_round

        while last_round < start_round + timeout:
            pending_txn = self.client.pending_transaction_info(tx_id)

            if pending_txn.get("confirmed-round", 0) > 0:
                return pending_txn

            if pending_txn["pool-error"]:
                raise RuntimeError("Pool error:")

            last_status = self.client.status_after_block(last_round + 1)

            last_round += 1

        raise RuntimeError(
            f"Transaction {tx_id} not confirmed after {timeout} rounds"
        )

    def create_amm_app(
        self,
        token: int,
        min_increment: int,
        deployer: Account
    ) -> int:
        """
        Creates a new amm.
        Args:
            deployer: The account that will create the amm application.
            token: The id of liquidity token in the liquidity pool,
            min_increment: min int to fund the pool
        Return:
            The ID of the newly created amm app.
        """
        self.stable_token = token
        approval, clear = get_contracts(self.client)

        global_schema = StateSchema(
            num_uints=13, num_byte_slices=1)
        local_schema = StateSchema(num_uints=0, num_byte_slices=0)

        app_args = [
            encoding.decode_address(deployer.public_key),
            token.to_bytes(8, "big"),
            min_increment.to_bytes(8, "big"),
        ]

        txn = ApplicationCreateTxn(
            sender=deployer.public_key,
            on_complete=OnComplete.NoOpOC,
            approval_program=approval,
            clear_program=clear,
            global_schema=global_schema,
            local_schema=local_schema,
            app_args=app_args,
            sp=self.client.suggested_params(),
        )

        signed_tx = txn.sign(deployer.private_key)

        self.client.send_transaction(signed_tx)

        response = self.wait_for_transaction(signed_tx.get_txid())
        assert response["application-index"] is not None and response["application-index"] > 0
        self.app_id = response["application-index"]
        self.update_app_address()
        return response["application-index"]

    def setup_amm_app(
        self,
        funder: Account
    ) -> int:
        """
        Finish setting up an amm.
        This operation funds the pool account, creates pool token,
        and opts app into tokens A and B, all in one atomic transaction group.
        Args:
            funder: The account providing the funding for the escrow account.
        Return: app asset ids.
        """

        fund_app_tx = PaymentTxn(
            sender=funder.public_key,
            receiver=self.app_addr,
            amt=MIN_BALANCE_REQUIREMENT,
            sp=self.client.suggested_params(),
        )

        setup_tx = ApplicationCallTxn(
            sender=funder.public_key,
            index=self.app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=[b"setup"],
            foreign_assets=[self.stable_token],
            sp=self.client.suggested_params(),
        )

        assign_group_id([fund_app_tx, setup_tx])

        signed_fund_spp_txn = fund_app_tx.sign(funder.private_key)
        signed_setup_tx = setup_tx.sign(funder.private_key)

        self.client.send_transactions([signed_fund_spp_txn, signed_setup_tx])

        self.wait_for_transaction(signed_fund_spp_txn.get_txid())
        glob_state = self.client.application_info(
            self.app_id)['params']['global-state']

        ids = {}

        for i, _ in enumerate(glob_state):
            if b64decode(glob_state[i]['key']) == b"pool_token_key":
                ids['pool_token_key'] = glob_state[i]['value']['uint']
                self.pool_token = glob_state[i]['value']['uint']
            elif b64decode(glob_state[i]['key']) == b"yes_token_key":
                ids['yes_token_key'] = glob_state[i]['value']['uint']
                self.yes_token = glob_state[i]['value']['uint']
            elif b64decode(glob_state[i]['key']) == b"no_token_key":
                ids['no_token_key'] = glob_state[i]['value']['uint']
                self.no_token = glob_state[i]['value']['uint']

        return ids

    def opt_in_to_pool_token(
        self,
        account: Account
    ) -> None:
        """
        Opts into Pool Token.
        Args:
            account: The account opting into the token.
        """

        opt_in_tx = AssetOptInTxn(
            sender=account.public_key, index=self.pool_token, sp=self.client.suggested_params()
        )

        signed_opt_in_tx = opt_in_tx.sign(account.private_key)

        self.client.send_transaction(signed_opt_in_tx)
        self.wait_for_transaction(signed_opt_in_tx.get_txid())

    def opt_in_to_no_token(
        self,
        account: Account
    ) -> None:
        """
        Opts into Pool Token.
        Args:
            account: The account opting into the token.
        """

        opt_in_tx = AssetOptInTxn(
            sender=account.public_key, index=self.no_token, sp=self.client.suggested_params()
        )

        signed_opt_in_tx = opt_in_tx.sign(account.private_key)

        self.client.send_transaction(signed_opt_in_tx)
        self.wait_for_transaction(signed_opt_in_tx.get_txid())

    def opt_in_to_yes_token(
        self,
        account: Account
    ) -> None:
        """
        Opts into Pool Token.
        Args:
            account: The account opting into the token.
        """

        opt_in_tx = AssetOptInTxn(
            sender=account.public_key, index=self.yes_token, sp=self.client.suggested_params()
        )

        signed_opt_in_tx = opt_in_tx.sign(account.private_key)

        self.client.send_transaction(signed_opt_in_tx)
        self.wait_for_transaction(signed_opt_in_tx.get_txid())

    def supply(
        self, quantity: int, supplier: Account
    ) -> None:
        """
        Supply liquidity to the pool.
        Args:
            quantity: quantity
            supplier: supplier
        """

        fee_tx = PaymentTxn(
            sender=supplier.public_key,
            receiver=self.app_addr,
            amt=MIN_BALANCE_REQUIREMENT,
            sp=self.client.suggested_params(),
        )

        token_tx = AssetTransferTxn(
            sender=supplier.public_key,
            receiver=self.app_addr,
            index=self.stable_token,
            amt=quantity,
            sp=self.client.suggested_params(),
        )

        app_call_tx = ApplicationCallTxn(
            sender=supplier.public_key,
            index=self.app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=[b"supply"],
            foreign_assets=[self.stable_token, self.pool_token,
                            self.yes_token, self.no_token],
            sp=self.client.suggested_params(),
        )

        assign_group_id([fee_tx, token_tx, app_call_tx])
        signed_fee_tx = fee_tx.sign(supplier.private_key)
        signed_token_tx = token_tx.sign(supplier.private_key)
        signed_app_call_tx = app_call_tx.sign(supplier.private_key)

        self.client.send_transactions(
            [signed_fee_tx, signed_token_tx, signed_app_call_tx]
        )
        self.wait_for_transaction(signed_app_call_tx.get_txid())

    def swap(
        self, option: str, quantity: int, supplier: Account
    ) -> None:
        """
        Swap stable for an AMM option.
        Args:
            option: string either yes or no option
            quantity: token amount
            supplier: account of the sender
        """
        if option == 'yes':
            second_argument = b"buy_yes"
        elif option == 'no':
            second_argument = b"buy_no"
        else:
            return

        fee_tx = PaymentTxn(
            sender=supplier.public_key,
            receiver=self.app_addr,
            amt=2_000,
            sp=self.client.suggested_params(),
        )

        token_tx = AssetTransferTxn(
            sender=supplier.public_key,
            receiver=self.app_addr,
            index=self.stable_token,
            amt=quantity,
            sp=self.client.suggested_params(),
        )

        app_call_tx = ApplicationCallTxn(
            sender=supplier.public_key,
            index=self.app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=[b"swap", second_argument],
            foreign_assets=[self.stable_token, self.pool_token,
                            self.yes_token, self.no_token],
            sp=self.client.suggested_params(),
        )

        assign_group_id([fee_tx, token_tx, app_call_tx])
        signed_fee_tx = fee_tx.sign(supplier.private_key)
        signed_token_tx = token_tx.sign(supplier.private_key)
        signed_app_call_tx = app_call_tx.sign(supplier.private_key)

        self.client.send_transactions(
            [signed_fee_tx, signed_token_tx, signed_app_call_tx]
        )
        self.wait_for_transaction(signed_app_call_tx.get_txid())

    def withdraw(
        self, pool_token_amount: int,
        withdrawal_account: Account
    ) -> None:
        """
        Withdraw liquidity  + rewards from the pool back to supplier.
        Supplier should receive stablecoin + fees proportional
        to the liquidity share in the pool they choose to withdraw.
        Args:
            pool_token_amount: token amount
            withdrawal_account: account of the sender to withdraw stablecoins
        """

        fee_tx = PaymentTxn(
            sender=withdrawal_account.public_key,
            receiver=self.app_addr,
            amt=2_000,
            sp=self.client.suggested_params(),
        )

        pool_token_tx = AssetTransferTxn(
            sender=withdrawal_account.public_key,
            receiver=self.app_addr,
            index=self.pool_token,
            amt=pool_token_amount,
            sp=self.client.suggested_params(),
        )

        app_call_tx = ApplicationCallTxn(
            sender=withdrawal_account.public_key,
            index=self.app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=[b"withdraw"],
            foreign_assets=[self.stable_token, self.pool_token],
            sp=self.client.suggested_params(),
        )

        assign_group_id([fee_tx, pool_token_tx, app_call_tx])
        signed_fee_tx = fee_tx.sign(withdrawal_account.private_key)
        signed_token_tx = pool_token_tx.sign(withdrawal_account.private_key)
        signed_app_call_tx = app_call_tx.sign(withdrawal_account.private_key)

        self.client.send_transactions(
            [signed_fee_tx, signed_token_tx, signed_app_call_tx])
        self.wait_for_transaction(signed_app_call_tx.get_txid())

    def redeem(
        self, token_in: int, token_amount: int,
        withdrawal_account: Account, token_out: int
    ) -> None:
        """
        Redeems winning token for stablecoin.
        First, pay for the fee incurred by AMM for sending back tokens A and B.
        Then conduct asset transfer and application call.
        Args:
            token_in: should be a winning token
            token_amount: token amount
            withdrawal_account: withdrawal account
            token_out: stablecoin
        """

        fee_tx = PaymentTxn(
            sender=withdrawal_account.public_key,
            receiver=self.app_addr,
            amt=2_000,
            sp=self.client.suggested_params(),
        )

        token_tx = AssetTransferTxn(
            sender=withdrawal_account.public_key,
            receiver=self.app_addr,
            index=token_in,
            amt=token_amount,
            sp=self.client.suggested_params(),
        )

        app_call_tx = ApplicationCallTxn(
            sender=withdrawal_account.public_key,
            index=self.app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=[b"redeem"],
            foreign_assets=[token_out, token_in],
            sp=self.client.suggested_params(),
        )

        assign_group_id([fee_tx, token_tx, app_call_tx])
        signed_fee_tx = fee_tx.sign(withdrawal_account.private_key)
        signed_token_tx = token_tx.sign(withdrawal_account.private_key)
        signed_app_call_tx = app_call_tx.sign(withdrawal_account.private_key)

        self.client.send_transactions(
            [signed_fee_tx, signed_token_tx, signed_app_call_tx])
        self.wait_for_transaction(signed_app_call_tx.get_txid())

    def set_result(
        self,
        funder: Account,
        second_argument
    ) -> None:
        """
        Sets result of the event.
        Args:
            funder: creator of the amm
            second_argument: result
        """

        fee_tx = PaymentTxn(
            sender=funder.public_key,
            receiver=self.app_addr,
            amt=2_000,
            sp=self.client.suggested_params(),
        )

        call_tx = ApplicationCallTxn(
            sender=funder.public_key,
            index=self.app_id,
            on_complete=OnComplete.NoOpOC,
            app_args=[b"result", second_argument],
            sp=self.client.suggested_params(),
        )

        assign_group_id([fee_tx, call_tx])
        signed_fee_tx = fee_tx.sign(funder.private_key)
        signed_app_call_tx = call_tx.sign(funder.private_key)

        self.client.send_transactions([signed_fee_tx, signed_app_call_tx])
        self.wait_for_transaction(signed_app_call_tx.get_txid())

    def close_amm(
        self,
        closing_account: Account
    ) -> None:
        """
        Closes an AMM.
        Args:
            closing_account: closer account public address.
            Must be the original creator of the pool.
        """

        delete_tx = ApplicationDeleteTxn(
            sender=closing_account.public_key,
            index=self.app_id,
            sp=self.client.suggested_params(),
        )
        signed_tx = delete_tx.sign(closing_account.private_key)

        self.client.send_transaction(signed_tx)

        self.wait_for_transaction(signed_tx.get_txid())
