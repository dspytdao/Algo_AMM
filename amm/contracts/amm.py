from pyteal import Bytes, Int,\
    TealType, Expr, \
    Btoi, \
    Global, App,\
    Txn, InnerTxnBuilder, TxnField, TxnType, InnerTxn, \
    OnComplete, Mode, \
    Approve, Reject, Assert, \
    Cond, If, Or, Seq, Not, \
    compileTeal


CREATOR_KEY = Bytes("creator_key")
TOKEN_A_KEY = Bytes("token_a_key")
TOKEN_B_KEY = Bytes("token_b_key")
POOL_TOKEN_KEY = Bytes("pool_token_key")
FEE_BPS_KEY = Bytes("fee_bps_key")
MIN_INCREMENT_KEY = Bytes("min_increment_key")
POOL_TOKENS_OUTSTANDING_KEY = Bytes("pool_tokens_outstanding_key")
SCALING_FACTOR = Int(10 ** 13)
POOL_TOKEN_DEFAULT_AMOUNT = Int(10 ** 13)


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

def optIn(token_key: TealType.bytes) -> Expr:
    return sendToken(token_key, Global.current_application_address(), Int(0))

def createPoolToken(pool_token_amount: TealType.uint64) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_total: pool_token_amount,
                TxnField.config_asset_default_frozen: Int(0),
                TxnField.config_asset_decimals: Int(0),
                TxnField.config_asset_reserve: Global.current_application_address(),
            }
        ),
        InnerTxnBuilder.Submit(),
        App.globalPut(POOL_TOKEN_KEY, InnerTxn.created_asset_id()),
        App.globalPut(POOL_TOKENS_OUTSTANDING_KEY, Int(0)),
    )

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
        optIn(TOKEN_A_KEY),
        optIn(TOKEN_B_KEY),
        Approve(),
    )


def approval_program():
    
    on_create = Seq(
        App.globalPut(CREATOR_KEY, Txn.application_args[0]),
        App.globalPut(TOKEN_A_KEY, Btoi(Txn.application_args[1])),
        App.globalPut(TOKEN_B_KEY, Btoi(Txn.application_args[2])),
        App.globalPut(FEE_BPS_KEY, Btoi(Txn.application_args[3])),
        App.globalPut(MIN_INCREMENT_KEY, Btoi(Txn.application_args[4])),
        Approve(),
    )

    on_setup = get_setup()
    on_supply = get_supply()
    on_withdraw = get_withdraw()
    on_swap = get_swap()

    on_call_method = Txn.application_args[0]
    on_call = Cond(
        [on_call_method == Bytes("setup"), on_setup],
        [on_call_method == Bytes("supply"), on_supply],
        [on_call_method == Bytes("withdraw"), on_withdraw],
        [on_call_method == Bytes("swap"), on_swap],
    )

    on_delete = Seq(
        If(App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) == Int(0)).Then(
            Seq(Assert(Txn.sender() == App.globalGet(CREATOR_KEY)), Approve())
        ),
        Reject(),
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


def clear_state_program():
    return Approve()

if __name__ == "__main__":
    with open("deposit_approval.teal", "w") as f:
        compiled = compileTeal(approval_program(), mode=Mode.Application, version=6)
        f.write(compiled)

    with open("deposit_clear_state.teal", "w") as f:
        compiled = compileTeal(clear_state_program(), mode=Mode.Application, version=6)
        f.write(compiled)