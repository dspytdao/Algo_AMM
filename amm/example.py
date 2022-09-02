""" example of the contract lifetime """
import os
from dotenv import load_dotenv
from algosdk import account
from algosdk.v2client import algod

from amm.create_asset import create_asset
from amm.amm_api import create_amm_app, setup_amm_app, opt_in_to_pool_token, \
    supply, swap

load_dotenv()

private_key = os.getenv('key')
creator = account.address_from_private_key(private_key)

algod_token = os.getenv('algod_token')

ALGOD_ADDRESS = "https://testnet-algorand.api.purestake.io/ps2"

headers = {
   "X-API-Key": algod_token,
}

# initialize an algodClient
client = algod.AlgodClient(algod_token, ALGOD_ADDRESS, headers)

# create (stable) asset
token = create_asset(client, private_key)

appID = create_amm_app(
    client=client,
    creator=creator,
    private_key=private_key,
    token=token,
    min_increment=1000,
)

print(f"Alice is setting up and funding amm {appID}")

Tokens = setup_amm_app(
    client=client,
    app_id=appID,
    funder=creator,
    private_key=private_key,
    token=token,
)

poolToken = Tokens['pool_token_key']
yesToken = Tokens['yes_token_key']
noToken = Tokens['no_token_key']

print(Tokens['pool_token_key'], Tokens['yes_token_key'], Tokens['no_token_key'])

opt_in_to_pool_token(client, creator, private_key, poolToken)
opt_in_to_pool_token(client, creator, private_key, yesToken)
opt_in_to_pool_token(client, creator, private_key, noToken)


print("Supplying AMM with initial token")

POOL_TOKEN_FIRST_AMOUNT = 500_000

supply(
    client=client,
    app_id=appID,
    quantity=POOL_TOKEN_FIRST_AMOUNT,
    supplier=creator,
    private_key=private_key,
    token=token,
    pool_token=poolToken,
    yes_token=yesToken,
    no_token=noToken
)

print("Supplying AMM with more tokens")

POOL_TOKEN_SECOND_AMOUNT = 1_500_000

supply(
    client=client,
    app_id=appID,
    quantity=POOL_TOKEN_SECOND_AMOUNT,
    supplier=creator,
    private_key=private_key,
    token=token,
    pool_token=poolToken,
    yes_token=yesToken,
    no_token=noToken
)

print("Swapping")

YES_TOKEN_AMOUNT = 100_000

# buy yes token
swap(
    client=client,
    app_id=appID,
    option="yes",
    quantity=YES_TOKEN_AMOUNT,
    supplier=creator,
    private_key=private_key,
    token=token,
    pool_token=poolToken,
    yes_token=yesToken,
    no_token=noToken
)

#buy no token
swap(
    client=client,
    app_id=appID,
    option="no",
    quantity=YES_TOKEN_AMOUNT,
    supplier=creator,
    private_key=private_key,
    token=token,
    pool_token=poolToken,
    yes_token=yesToken,
    no_token=noToken
)

print("Withdrawing")

ALL_TOKENS = 2_000_000

"""
withdraw(
    client = client,
    appID = appID,
    poolTokenAmount = ALL_TOKENS, poolToken = poolToken,
    withdrawAccount = creator, private_key = private_key, token = token
)

print("Result")
#set winner

set_result(
    client = client,
    appID = appID,
    second_argument=b"yes",
    funder=creator,
    private_key = private_key
)


# redemption for for yes/no

print("Redeeming")

YesTokensAmount = 95_238

redeem(
    client = client,
    appID = appID,
    TokenAmount = YesTokensAmount,
    Token = yesToken,
    withdrawAccount = creator, private_key = private_key, token = token
)

# Delete

print("Deleting")

close_amm(
    client = client,
    appID = appID,
    closer=creator,
    private_key = private_key
) """
