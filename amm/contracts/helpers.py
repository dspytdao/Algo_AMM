from pyteal import *

from contracts.config import (
    POOL_TOKENS_OUTSTANDING_KEY, POOL_TOKEN_KEY, POOL_FUNDING_RESERVES,
    YES_TOKEN_KEY, YES_TOKENS_OUTSTANDING_KEY, YES_TOKENS_RESERVES,
    NO_TOKEN_KEY, NO_TOKENS_OUTSTANDING_KEY, NO_TOKENS_RESERVES,
    TOKEN_FUNDING_KEY, TOKEN_FUNDING_RESERVES, RESULT
)


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
        App.globalPut(NO_TOKENS_RESERVES,  amount + App.globalGet(NO_TOKENS_RESERVES) ),
        App.globalPut(YES_TOKENS_RESERVES, amount + App.globalGet(YES_TOKENS_RESERVES) ),
        App.globalPut(
            POOL_FUNDING_RESERVES, App.globalGet(POOL_FUNDING_RESERVES) + amount
        ),
    )


def mintAndSendNoToken(receiver: TealType.bytes, amount: TealType.uint64) -> Expr:
    funding = AssetHolding.balance(
        Global.current_application_address(), App.globalGet(TOKEN_FUNDING_KEY)
    )
    tokensOut: ScratchVar = ScratchVar(TealType.uint64)
    return Seq(
        tokensOut.store(
            App.globalGet(YES_TOKENS_RESERVES) * amount / (App.globalGet(NO_TOKENS_RESERVES) + amount ) #* (Int(10000) - App.globalGet(FEE_BPS_KEY)) / Int(10000)
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


def mintAndSendYesToken(receiver: TealType.bytes, amount: TealType.uint64) -> Expr:
    funding = AssetHolding.balance(
        Global.current_application_address(), App.globalGet(TOKEN_FUNDING_KEY)
    )
    tokensOut: ScratchVar = ScratchVar(TealType.uint64)
    return Seq(
        tokensOut.store(
            (App.globalGet(NO_TOKENS_RESERVES) * amount / (App.globalGet(YES_TOKENS_RESERVES) + amount )) #* (Int(10000) - App.globalGet(FEE_BPS_KEY)) / Int(10000)
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
    )

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
        App.globalPut(
            YES_TOKENS_OUTSTANDING_KEY, App.globalGet(YES_TOKENS_OUTSTANDING_KEY) - result_token_amount
        ),
    )