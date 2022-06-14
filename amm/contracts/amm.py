from pyteal import *

from contracts.helpers import validateTokenReceived, mintAndSendPoolToken, \
                                optIn, createPoolToken, withdrawGivenPoolToken
                                #, tryTakeAdjustedAmounts, 

from contracts.config import CREATOR_KEY, TOKEN_FUNDING_KEY, \
    POOL_TOKEN_KEY, FEE_BPS_KEY, MIN_INCREMENT_KEY, \
    POOL_TOKENS_OUTSTANDING_KEY, SCALING_FACTOR, POOL_TOKEN_DEFAULT_AMOUNT


def get_setup():
    # if the amm has been set up, pool token id and outstanding value already exists
    pool_token_id = App.globalGetEx(Global.current_application_id(), POOL_TOKEN_KEY)
    pool_tokens_outstanding = App.globalGetEx(
        Global.current_application_id(), POOL_TOKENS_OUTSTANDING_KEY
    )
    return Seq(
        pool_token_id,
        pool_tokens_outstanding,
        # can only set up once
        Assert(Not(pool_token_id.hasValue())),
        Assert(Not(pool_tokens_outstanding.hasValue())),
        createPoolToken(POOL_TOKEN_DEFAULT_AMOUNT),
        optIn(TOKEN_FUNDING_KEY),
        Approve(),
    )

token_funding_holding = AssetHolding.balance(
    Global.current_application_address(), App.globalGet(TOKEN_FUNDING_KEY)
)


# supply initial liquidity, receive pool token
# 
def get_supply():
    token_txn_index = Txn.group_index() - Int(1)

    pool_token_holding = AssetHolding.balance(
        Global.current_application_address(), App.globalGet(POOL_TOKEN_KEY)
    )

    token_before_txn: ScratchVar = ScratchVar(TealType.uint64)

    on_supply = Seq(
        pool_token_holding,
        token_funding_holding,
        Assert(
            And(
                pool_token_holding.hasValue(),
                pool_token_holding.value() > Int(0),
                validateTokenReceived(token_txn_index, TOKEN_FUNDING_KEY),
                Gtxn[token_txn_index].asset_amount()
                >= App.globalGet(MIN_INCREMENT_KEY),
            )
        ),
        token_before_txn.store(
            token_funding_holding.value() - Gtxn[token_txn_index].asset_amount()
        ),
        If(
                token_before_txn.load() == Int(0),
        )
        .Then(
            # no liquidity yet
            Seq(
                mintAndSendPoolToken(
                    Txn.sender(),
                    Gtxn[token_txn_index].asset_amount(),
                ),
                Approve(),
            ),
        )
        .Else(Reject()),
    )
    return on_supply


def get_withdraw():
    pool_token_txn_index = Txn.group_index() - Int(1)
    on_withdraw =  on_withdraw = Seq(
        token_funding_holding ,
        Assert(
            And(
                token_funding_holding .hasValue(),
                token_funding_holding .value() > Int(0),
                validateTokenReceived(pool_token_txn_index, POOL_TOKEN_KEY),
            )
        ),
        If(Gtxn[pool_token_txn_index].asset_amount() > Int(0)).Then(
            Seq(
                withdrawGivenPoolToken(
                    Txn.sender(),
                    TOKEN_FUNDING_KEY,
                    Gtxn[pool_token_txn_index].asset_amount(),
                    App.globalGet(POOL_TOKENS_OUTSTANDING_KEY),
                ),
                App.globalPut(
                    POOL_TOKENS_OUTSTANDING_KEY,
                    App.globalGet(POOL_TOKENS_OUTSTANDING_KEY)
                    - Gtxn[pool_token_txn_index].asset_amount(),
                ),
                Approve(),
            ),
        ),
        Reject(),
    )


    return on_withdraw


def approval_program():
    
    on_create = Seq(
        App.globalPut(CREATOR_KEY, Txn.application_args[0]),
        App.globalPut(TOKEN_FUNDING_KEY, Btoi(Txn.application_args[1])),
        App.globalPut(FEE_BPS_KEY, Btoi(Txn.application_args[2])),
        App.globalPut(MIN_INCREMENT_KEY, Btoi(Txn.application_args[3])),
        Approve(),
    )

    on_setup = get_setup()
    on_supply = get_supply()
    on_withdraw = get_withdraw()

    on_call_method = Txn.application_args[0]
    on_call = Cond(
        [on_call_method == Bytes("setup"), on_setup],#2
        [on_call_method == Bytes("supply"), on_supply],#3
        [on_call_method == Bytes("withdraw"), on_withdraw],#3
    )

    on_delete = Seq(
        If(App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) == Int(0)).Then(
            Seq(Assert(Txn.sender() == App.globalGet(CREATOR_KEY)), Approve())
        ),
        Reject(),
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