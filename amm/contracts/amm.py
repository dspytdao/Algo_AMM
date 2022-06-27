from pyteal import *

from contracts.helpers import (
    validateTokenReceived, mintAndSendPoolToken,
    mintAndSendNoToken, mintAndSendYesToken,
    optIn, createPoolToken, withdrawLPToken,
    createNoToken, createYesToken, redeemToken
    )

from contracts.config import (
    CREATOR_KEY, TOKEN_FUNDING_KEY,
    POOL_TOKEN_KEY, MIN_INCREMENT_KEY,
    POOL_TOKENS_OUTSTANDING_KEY, TOKEN_DEFAULT_AMOUNT,
    YES_TOKEN_KEY, NO_TOKEN_KEY,
    TOKEN_FUNDING_RESERVES, POOL_FUNDING_RESERVES,
    RESULT
)


def get_setup():

    return Seq(
        createPoolToken(TOKEN_DEFAULT_AMOUNT),
        optIn(TOKEN_FUNDING_KEY),
        createNoToken(TOKEN_DEFAULT_AMOUNT),
        optIn(NO_TOKEN_KEY),
        createYesToken(TOKEN_DEFAULT_AMOUNT),
        optIn(YES_TOKEN_KEY),
        Approve(),
    )

# supply liquidity, receive pool token
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


def get_withdraw():

    pool_token_txn_index = Txn.group_index() - Int(1)
    on_withdraw = Seq(
        Assert(
            And(
                validateTokenReceived(pool_token_txn_index, POOL_TOKEN_KEY),
                Gtxn[pool_token_txn_index].asset_amount() > Int(0),
            )
        ),
        withdrawLPToken(
            Txn.sender(),
            Gtxn[pool_token_txn_index].asset_amount(),
        ),
        Approve(),
    )

    return on_withdraw


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


def get_redemption():

    token_txn_index = Txn.group_index() - Int(1)
    on_withdraw = Seq(
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

    return on_withdraw


def approval_program():
    
    on_create = Seq(
        App.globalPut(CREATOR_KEY, Txn.application_args[0]),
        App.globalPut(TOKEN_FUNDING_KEY, Btoi(Txn.application_args[1])),
        App.globalPut(TOKEN_FUNDING_RESERVES, Int(0)),
        App.globalPut(POOL_FUNDING_RESERVES, Int(0)),
        App.globalPut(MIN_INCREMENT_KEY, Btoi(Txn.application_args[2])),
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
        [on_call_method == Bytes("setup"), on_setup],#2
        [on_call_method == Bytes("supply"), on_supply],#3
        [on_call_method == Bytes("withdraw"), on_withdraw],#
        [on_call_method == Bytes("redeem"), on_redemption],#
        [on_call_method == Bytes("result"), on_result],
        [on_call_method == Bytes("swap"), on_swap],#4
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
        [Txn.application_id() == Int(0), on_create],#1
        [Txn.on_completion() == OnComplete.NoOp, on_call],#2, 3
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
    return Approve()

if __name__ == "__main__":
    with open("deposit_approval.teal", "w") as f:
        compiled = compileTeal(approval_program(), mode=Mode.Application, version=6)
        f.write(compiled)

    with open("deposit_clear.teal", "w") as f:
        compiled = compileTeal(clear_program(), mode=Mode.Application, version=6)
        f.write(compiled)