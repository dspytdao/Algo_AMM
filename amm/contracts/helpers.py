from pyteal import *

from contracts.config import (
    POOL_TOKENS_OUTSTANDING_KEY, POOL_TOKEN_KEY,
    YES_TOKEN_KEY, YES_TOKENS_OUTSTANDING_KEY,
    NO_TOKEN_KEY, NO_TOKENS_OUTSTANDING_KEY,
    NO_TOKENS_RESERVES, YES_TOKENS_RESERVES
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


def AddNoToken(token_amount: TealType.uint64):
    return Seq(
        App.globalPut(NO_TOKENS_RESERVES, App.globalGet(NO_TOKENS_RESERVES) + token_amount),
    )


def createYesToken(token_amount: TealType.uint64) -> Expr:
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.type_enum: TxnType.AssetConfig,
                TxnField.config_asset_total: token_amount,
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


def AddYesToken(token_amount: TealType.uint64):
    return Seq(
        App.globalPut(YES_TOKENS_RESERVES, App.globalGet(YES_TOKENS_RESERVES) + token_amount),
    )


def withdrawGivenPoolToken(
    receiver: TealType.bytes,
    to_withdraw_token_key: TealType.bytes,
    pool_token_amount: TealType.uint64,
    pool_tokens_outstanding: TealType.uint64,
) -> Expr:
    token_holding = AssetHolding.balance(
        Global.current_application_address(), App.globalGet(to_withdraw_token_key)
    )
    return Seq(
        token_holding,
        If(
            And(
                pool_tokens_outstanding > Int(0),
                pool_token_amount > Int(0),
                token_holding.hasValue(),
                token_holding.value() > Int(0),
            )
        ).Then(
            Seq(
                sendToken(
                    to_withdraw_token_key,
                    receiver,
                    pool_token_amount,
                ),
            )
        ),
    )


def mintAndSendPoolToken(receiver: TealType.bytes, amount: TealType.uint64) -> Expr:
    return Seq(
        sendToken(POOL_TOKEN_KEY, receiver, amount),
        App.globalPut(
            POOL_TOKENS_OUTSTANDING_KEY,
            App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) + amount,
        ),
    )


def mintAndSendNoToken(receiver: TealType.bytes, amount: TealType.uint64) -> Expr:
    tokensOut: ScratchVar = ScratchVar(TealType.uint64)
    return Seq(
        tokensOut.store(
            App.globalGet(YES_TOKENS_RESERVES) * amount / (App.globalGet(NO_TOKENS_RESERVES) + amount)
        ),
        App.globalPut(NO_TOKENS_OUTSTANDING_KEY, App.globalGet(NO_TOKENS_OUTSTANDING_KEY) + tokensOut.load()),
        App.globalPut(NO_TOKENS_RESERVES, App.globalGet(NO_TOKENS_RESERVES) - tokensOut.load()),
        sendToken(NO_TOKEN_KEY, receiver, tokensOut.load()),
    )


def mintAndSendYesToken(receiver: TealType.bytes, amount: TealType.uint64) -> Expr:
    tokensOut: ScratchVar = ScratchVar(TealType.uint64)
    return Seq(
        tokensOut.store(
            App.globalGet(NO_TOKENS_RESERVES) * amount / (App.globalGet(YES_TOKENS_RESERVES)+amount)
        ),
        App.globalPut(YES_TOKENS_OUTSTANDING_KEY, App.globalGet(YES_TOKENS_OUTSTANDING_KEY) + tokensOut.load()),
        App.globalPut(YES_TOKENS_RESERVES, App.globalGet(YES_TOKENS_RESERVES) - tokensOut.load()),
        sendToken(YES_TOKEN_KEY, receiver, tokensOut.load()),
    )
