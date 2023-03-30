"""main"""
from pyteal import (App, Global, Assert, Seq, And, Not, Txn, Int,
                    Approve, Gtxn, If, Bytes, Reject, Btoi, Cond, Or, OnComplete, compileTeal, Mode)

from amm.contracts.helpers import (
    validate_token_received, mint_and_send_pool_token,
    mint_and_send_no_token, mint_and_send_yes_token,
    opt_in, create_pool_token, withdraw_lp_token,
    create_no_token, create_yes_token, redeem_token
)

from amm.contracts.config import (
    CREATOR_KEY, TOKEN_FUNDING_KEY,
    POOL_TOKEN_KEY, MIN_INCREMENT_KEY,
    POOL_TOKENS_OUTSTANDING_KEY, TOKEN_DEFAULT_AMOUNT,
    YES_TOKEN_KEY, NO_TOKEN_KEY,
    TOKEN_FUNDING_RESERVES, POOL_FUNDING_RESERVES,
    RESULT
)


def get_setup():
    """sets up contract"""
    pool_token_id = App.globalGetEx(
        Global.current_application_id(), POOL_TOKEN_KEY)
    pool_tokens_outstanding = App.globalGetEx(
        Global.current_application_id(), POOL_TOKENS_OUTSTANDING_KEY
    )
    on_setup = Seq(
        pool_token_id,
        pool_tokens_outstanding,
        Assert(Not(pool_token_id.hasValue())),
        Assert(Not(pool_tokens_outstanding.hasValue())),
        create_pool_token(TOKEN_DEFAULT_AMOUNT),
        opt_in(TOKEN_FUNDING_KEY),
        create_no_token(TOKEN_DEFAULT_AMOUNT),
        opt_in(NO_TOKEN_KEY),
        create_yes_token(TOKEN_DEFAULT_AMOUNT),
        opt_in(YES_TOKEN_KEY),
        Approve(),
    )
    return on_setup


def get_supply():
    """liquidity supply"""
    token_txn_index = Txn.group_index() - Int(1)

    on_supply = Seq(
        Assert(
            And(
                validate_token_received(token_txn_index, TOKEN_FUNDING_KEY),
                Gtxn[token_txn_index].asset_amount()
                >= App.globalGet(MIN_INCREMENT_KEY),
            )
        ),
        mint_and_send_pool_token(
            Txn.sender(),
            Gtxn[token_txn_index].asset_amount(),
        ),
        Approve(),
    )
    return on_supply


def get_swap():
    """option swap"""
    token_txn_index = Txn.group_index() - Int(1)
    option = Txn.application_args[1]
    on_swap = Seq(
        Assert(
            validate_token_received(token_txn_index, TOKEN_FUNDING_KEY),
        ),
        If(option == Bytes("buy_yes"))
        .Then(
            Seq(
                mint_and_send_yes_token(
                    Txn.sender(),
                    Gtxn[token_txn_index].asset_amount(),
                ),
                Approve()
            ),
        )
        .ElseIf(option == Bytes("buy_no"))
        .Then(
            Seq(
                mint_and_send_no_token(
                    Txn.sender(),
                    Gtxn[token_txn_index].asset_amount(),
                ),
                Approve()
            ),
        ),
        Reject()
    )

    return on_swap


def get_withdraw():
    """liquidity withdrawal"""
    pool_token_txn_index = Txn.group_index() - Int(1)

    on_withdraw = Seq(
        Assert(
            validate_token_received(pool_token_txn_index, POOL_TOKEN_KEY),
        ),
        withdraw_lp_token(
            Txn.sender(),
            Gtxn[pool_token_txn_index].asset_amount(),
        ),
        Approve(),
    )

    return on_withdraw


def get_result():
    """sets result"""
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


def get_redemption():
    """redeems winning tokens"""
    token_txn_index = Txn.group_index() - Int(1)

    on_redemption = Seq(
        Assert(
            And(
                validate_token_received(token_txn_index, RESULT),
            )
        ),
        redeem_token(
            Txn.sender(),
            Gtxn[token_txn_index].asset_amount(),
        ),
        Approve(),
    )

    return on_redemption


def approval_program():
    """main"""
    on_create = Seq(
        App.globalPut(CREATOR_KEY, Txn.application_args[0]),
        App.globalPut(TOKEN_FUNDING_KEY, Btoi(Txn.application_args[1])),
        App.globalPut(MIN_INCREMENT_KEY, Btoi(Txn.application_args[2])),
        App.globalPut(TOKEN_FUNDING_RESERVES, Int(0)),
        App.globalPut(POOL_FUNDING_RESERVES, Int(0)),
        App.globalPut(RESULT, Int(0)),
        Approve(),
    )

    on_setup = get_setup()
    on_supply = get_supply()
    on_swap = get_swap()
    on_withdraw = get_withdraw()
    on_redemption = get_redemption()
    on_result = get_result()

    on_call_method = Txn.application_args[0]
    on_call = Cond(
        [on_call_method == Bytes("setup"), on_setup],
        [on_call_method == Bytes("supply"), on_supply],
        [on_call_method == Bytes("withdraw"), on_withdraw],
        [on_call_method == Bytes("swap"), on_swap],
        [on_call_method == Bytes("redeem"), on_redemption],
        [on_call_method == Bytes("result"), on_result],
    )

    on_delete = Seq(
        Assert(
            And(
                Txn.sender() == App.globalGet(CREATOR_KEY),
                App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) == Int(0),
            ),
        ),
        Approve(),
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

    return program


def clear_program():
    """clear program"""
    return Approve()


if __name__ == "__main__":
    with open("deposit_approval.teal", "w", encoding="utf-8") as f:
        COMPILED = compileTeal(
            approval_program(), mode=Mode.Application, version=6)
        f.write(COMPILED)

    with open("deposit_clear.teal", "w", encoding="utf-8") as f:
        COMPILED = compileTeal(
            clear_program(), mode=Mode.Application, version=6)
        f.write(COMPILED)
