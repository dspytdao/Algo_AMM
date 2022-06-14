from pyteal import *

from contracts.config import (
    SCALING_FACTOR,
    POOL_TOKENS_OUTSTANDING_KEY,
    POOL_TOKEN_KEY,
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


#def xMulYDivZ(x, y, z) -> Expr:
#    return WideRatio([x, y, SCALING_FACTOR], [z, SCALING_FACTOR])


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


#create two additional tokens as well
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


def assessFee(amount: TealType.uint64, fee_bps: TealType.uint64):
    fee_num = Int(10000) - fee_bps
    fee_denom = Int(10000)
    return xMulYDivZ(amount, fee_num, fee_denom)


def computeOtherTokenOutputPerGivenTokenInput(
    input_amount: TealType.uint64,
    previous_given_token_amount: TealType.uint64,
    previous_other_token_amount: TealType.uint64,
    fee_bps: TealType.uint64,
):
    k = previous_given_token_amount * previous_other_token_amount
    amount_sub_fee = assessFee(input_amount, fee_bps)
    to_send = previous_other_token_amount - k / (
        previous_given_token_amount + amount_sub_fee
    )
    return to_send


def mintAndSendPoolToken(receiver: TealType.bytes, amount: TealType.uint64) -> Expr:
    return Seq(
        sendToken(POOL_TOKEN_KEY, receiver, amount),
        App.globalPut(
            POOL_TOKENS_OUTSTANDING_KEY,
            App.globalGet(POOL_TOKENS_OUTSTANDING_KEY) + amount,
        ),
    )