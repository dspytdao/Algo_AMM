"""helper pyteal functions"""
from pyteal import (App, Global, TxnType, Seq, And, TealType, Txn, Int, Expr,
                    Gtxn, If, Bytes, InnerTxnBuilder, TxnField, InnerTxn, ScratchVar, AssetHolding)

from amm.contracts.config import (
    POOL_TOKENS_OUTSTANDING_KEY, POOL_TOKEN_KEY, POOL_FUNDING_RESERVES, RESULT,
    YES_TOKEN_KEY, YES_TOKENS_OUTSTANDING_KEY, YES_TOKENS_RESERVES,
    NO_TOKEN_KEY, NO_TOKENS_OUTSTANDING_KEY, NO_TOKENS_RESERVES,
    TOKEN_FUNDING_KEY, TOKEN_FUNDING_RESERVES
)


def validate_token_received(
    transaction_index: TealType.uint64, token_key: TealType.bytes
) -> Expr:
    """validate token type, sender, asset """
    return And(
        Gtxn[transaction_index].type_enum() == TxnType.AssetTransfer,
        Gtxn[transaction_index].sender() == Txn.sender(),
        Gtxn[transaction_index].asset_receiver()
        == Global.current_application_address(),
        Gtxn[transaction_index].xfer_asset() == App.globalGet(token_key),
        Gtxn[transaction_index].asset_amount() > Int(0),
    )


def send_token(
    token_key: TealType.bytes, receiver: TealType.bytes, amount: TealType.uint64
) -> Expr:
    """asa token transfer"""
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


def opt_in(token_key: TealType.bytes) -> Expr:
    """asa opt in"""
    return send_token(token_key, Global.current_application_address(), Int(0))


def create_pool_token(pool_token_amount: TealType.uint64) -> Expr:
    """creates asa token"""
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


def create_no_token(token_amount: TealType.uint64) -> Expr:
    """creates asa token"""
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


def create_yes_token(token_amount: TealType.uint64) -> Expr:
    """creates asa token"""
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


def mint_and_send_pool_token(receiver: TealType.bytes, amount: TealType.uint64) -> Expr:
    """mintAndSendPoolToken"""
    ratio: ScratchVar = ScratchVar(TealType.uint64)
    no_reserves = App.globalGet(NO_TOKENS_RESERVES)
    return Seq(
        ratio.store(
            (Int(1) + App.globalGet(NO_TOKENS_RESERVES)) /
            (Int(1) + App.globalGet(YES_TOKENS_RESERVES))),
        If(App.globalGet(POOL_FUNDING_RESERVES) > Int(0)).Then(
            Seq(
                send_token(
                    POOL_TOKEN_KEY, receiver, amount * App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) /
                    App.globalGet(POOL_FUNDING_RESERVES)),
                App.globalPut(
                    POOL_TOKENS_OUTSTANDING_KEY, App.globalGet(
                        POOL_TOKENS_OUTSTANDING_KEY) + amount
                    * App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) / App.globalGet(
                        POOL_FUNDING_RESERVES)))).ElseIf(
            App.globalGet(POOL_FUNDING_RESERVES) == Int(0)).Then(
            Seq(
                send_token(POOL_TOKEN_KEY, receiver, amount),
                App.globalPut(
                    POOL_TOKENS_OUTSTANDING_KEY, App.globalGet(
                        POOL_TOKENS_OUTSTANDING_KEY)
                    + amount,),)),
        App.globalPut(
            NO_TOKENS_RESERVES, ratio.load() * (amount / Int(4)) + no_reserves),
        App.globalPut(
            YES_TOKENS_RESERVES, (Int(1) / ratio.load()) * (amount / Int(4)) + App.globalGet(
                YES_TOKENS_RESERVES)),
        App.globalPut(POOL_FUNDING_RESERVES, App.globalGet(POOL_FUNDING_RESERVES) + amount),)


def mint_and_send_no_token(
    receiver: TealType.bytes, amount: TealType.uint64
) -> Expr:
    """mints no token"""
    funding = AssetHolding.balance(
        Global.current_application_address(), App.globalGet(TOKEN_FUNDING_KEY)
    )
    tokens_out: ScratchVar = ScratchVar(TealType.uint64)
    return Seq(
        tokens_out.store(
            App.globalGet(NO_TOKENS_RESERVES) * amount /
            (App.globalGet(YES_TOKENS_RESERVES) + amount)
        ),
        App.globalPut(NO_TOKENS_OUTSTANDING_KEY,
                      App.globalGet(NO_TOKENS_OUTSTANDING_KEY) + tokens_out.load()),
        App.globalPut(NO_TOKENS_RESERVES, App.globalGet(
            NO_TOKENS_RESERVES) - tokens_out.load()),
        send_token(NO_TOKEN_KEY, receiver, tokens_out.load()),
        If(App.globalGet(NO_TOKENS_OUTSTANDING_KEY) >
           App.globalGet(YES_TOKENS_OUTSTANDING_KEY))
        .Then(
            App.globalPut(TOKEN_FUNDING_RESERVES, App.globalGet(
                NO_TOKENS_OUTSTANDING_KEY) * Int(2))
        ),
        funding,
        App.globalPut(
            POOL_FUNDING_RESERVES,
            funding.value() - App.globalGet(TOKEN_FUNDING_RESERVES)
        ),
    )


def mint_and_send_yes_token(
    receiver: TealType.bytes, amount: TealType.uint64
) -> Expr:
    """mints yes token"""
    funding = AssetHolding.balance(
        Global.current_application_address(), App.globalGet(TOKEN_FUNDING_KEY)
    )
    tokens_out: ScratchVar = ScratchVar(TealType.uint64)
    return Seq(
        tokens_out.store(
            (App.globalGet(YES_TOKENS_RESERVES) * amount /
             (App.globalGet(NO_TOKENS_RESERVES) + amount))
        ),
        App.globalPut(YES_TOKENS_OUTSTANDING_KEY,
                      App.globalGet(YES_TOKENS_OUTSTANDING_KEY) + tokens_out.load()),
        App.globalPut(YES_TOKENS_RESERVES, App.globalGet(
            YES_TOKENS_RESERVES) - tokens_out.load()),
        send_token(YES_TOKEN_KEY, receiver, tokens_out.load()),
        If(App.globalGet(YES_TOKENS_OUTSTANDING_KEY)
           > App.globalGet(NO_TOKENS_OUTSTANDING_KEY))
        .Then(
            App.globalPut(TOKEN_FUNDING_RESERVES,
                          App.globalGet(YES_TOKENS_OUTSTANDING_KEY) * Int(2)
                          )
        ),
        funding,
        App.globalPut(
            POOL_FUNDING_RESERVES,
            funding.value() - App.globalGet(TOKEN_FUNDING_RESERVES)
        ),
    )


def withdraw_lp_token(
    receiver: TealType.bytes,
    pool_token_amount: TealType.uint64,
) -> Expr:
    """withdraws lp token"""
    ratio: ScratchVar = ScratchVar(TealType.uint64)
    total = App.globalGet(POOL_TOKENS_OUTSTANDING_KEY)
    reserves = App.globalGet(POOL_FUNDING_RESERVES)

    return Seq(
        send_token(
            TOKEN_FUNDING_KEY,
            receiver,
            App.globalGet(POOL_FUNDING_RESERVES) *
            pool_token_amount / App.globalGet(POOL_TOKENS_OUTSTANDING_KEY),
        ),
        App.globalPut(
            POOL_FUNDING_RESERVES,
            App.globalGet(POOL_FUNDING_RESERVES) - (App.globalGet(POOL_FUNDING_RESERVES) *
                                                    pool_token_amount / total),
        ),
        App.globalPut(
            POOL_TOKENS_OUTSTANDING_KEY,
            App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) - pool_token_amount,
        ),
        If(App.globalGet(RESULT) == Int(0)).Then(
            Seq(
                ratio.store(
                    (Int(1) + App.globalGet(NO_TOKENS_RESERVES))
                    / (Int(1) + App.globalGet(YES_TOKENS_RESERVES))
                ),
                App.globalPut(NO_TOKENS_RESERVES,
                              App.globalGet(NO_TOKENS_RESERVES) - (reserves *
                                                                   pool_token_amount / total) /
                              Int(4) * ratio.load()),
                App.globalPut(YES_TOKENS_RESERVES,
                              App.globalGet(YES_TOKENS_RESERVES) - (reserves *
                                                                    pool_token_amount / total) /
                              Int(4) * (Int(1)/ratio.load())),
            )),
    )


def redeem_token(
    receiver: TealType.bytes,
    result_token_amount: TealType.uint64,
) -> Expr:
    """redeems token"""
    return Seq(
        send_token(
            TOKEN_FUNDING_KEY,
            receiver,
            result_token_amount * Int(2)
        ),
        App.globalPut(
            TOKEN_FUNDING_RESERVES,
            App.globalGet(TOKEN_FUNDING_RESERVES) -
            result_token_amount * Int(2)
        ),
        If(App.globalGet(RESULT) == App.globalGet(YES_TOKEN_KEY))
        .Then(
            App.globalPut(
                YES_TOKENS_OUTSTANDING_KEY,
                App.globalGet(YES_TOKENS_OUTSTANDING_KEY) - result_token_amount
            ),
        )
        .ElseIf(App.globalGet(RESULT) == App.globalGet(NO_TOKEN_KEY))
        .Then(
            App.globalPut(
                NO_TOKENS_OUTSTANDING_KEY,
                App.globalGet(NO_TOKENS_OUTSTANDING_KEY) - result_token_amount
            ),
        ),
    )
