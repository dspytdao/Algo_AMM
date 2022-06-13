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


def xMulYDivZ(x, y, z) -> Expr:
    return WideRatio([x, y, SCALING_FACTOR], [z, SCALING_FACTOR])


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


def optIn(token_key: TealType.bytes) -> Expr:
    return sendToken(token_key, Global.current_application_address(), Int(0))


def returnRemainder(
    token_key: TealType.bytes,
    received_amount: TealType.uint64,
    to_keep_amount: TealType.uint64,
) -> Expr:
    remainder = received_amount - to_keep_amount
    return Seq(
        If(remainder > Int(0)).Then(
            sendToken(
                token_key,
                Txn.sender(),
                remainder,
            )
        ),
    )


def tryTakeAdjustedAmounts(
    to_keep_token_txn_amt: TealType.uint64,
    to_keep_token_before_txn_amt: TealType.uint64,
    other_token_key: TealType.bytes,
    other_token_txn_amt: TealType.uint64,
    other_token_before_txn_amt: TealType.uint64,
) -> Expr:
    """
    Given supplied token amounts, try to keep all of one token and the corresponding amount of other token
    as determined by market price before transaction. If corresponding amount is less than supplied, send the remainder back.
    If successful, mint and sent pool tokens in proportion to new liquidity over old liquidity.
    """
    other_corresponding_amount = ScratchVar(TealType.uint64)

    return Seq(
        other_corresponding_amount.store(
            xMulYDivZ(
                to_keep_token_txn_amt,
                other_token_before_txn_amt,
                to_keep_token_before_txn_amt,
            )
        ),
        If(
            And(
                other_corresponding_amount.load() > Int(0),
                other_token_txn_amt >= other_corresponding_amount.load(),
            )
        ).Then(
            Seq(
                returnRemainder(
                    other_token_key,
                    other_token_txn_amt,
                    other_corresponding_amount.load(),
                ),
                mintAndSendPoolToken(
                    Txn.sender(),
                    xMulYDivZ(
                        App.globalGet(POOL_TOKENS_OUTSTANDING_KEY),
                        to_keep_token_txn_amt,
                        to_keep_token_before_txn_amt,
                    ),
                ),
                Return(Int(1)),
            )
        ),
        Return(Int(0)),
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
                Assert(
                    xMulYDivZ(
                        token_holding.value(),
                        pool_token_amount,
                        pool_tokens_outstanding,
                    )
                    > Int(0)
                ),
                sendToken(
                    to_withdraw_token_key,
                    receiver,
                    xMulYDivZ(
                        token_holding.value(),
                        pool_token_amount,
                        pool_tokens_outstanding,
                    ),
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