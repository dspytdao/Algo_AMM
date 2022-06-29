import os
from dotenv import load_dotenv
from algosdk import account
from algosdk.v2client import algod

from create_asset import create_asset
from amm_api import createAmmApp, setupAmmApp, optInToPoolToken, \
    supply, withdraw, swap, set_result, closeAmm, redeem


load_dotenv()

private_key = os.getenv('key')
creator = account.address_from_private_key(private_key)

algod_token = os.getenv('algod_token')

algod_address = "https://testnet-algorand.api.purestake.io/ps2"

headers = {
   "X-API-Key": algod_token,
}

# initialize an algodClient
client = algod.AlgodClient(algod_token, algod_address, headers)

#create (stable) asset
token = create_asset(client, private_key)

appID = createAmmApp(
    client=client,
    creator=creator,
    private_key=private_key,
    token=token,
    minIncrement=1000,
)

print(f"Alice is setting up and funding amm {appID}")

Tokens = setupAmmApp(
    client=client,
    appID=appID,
    funder=creator,
    private_key=private_key,
    token=token,
)

poolToken = Tokens['pool_token_key']
yesToken = Tokens['yes_token_key']
noToken = Tokens['no_token_key']

print(Tokens['pool_token_key'], Tokens['yes_token_key'], Tokens['no_token_key'])

optInToPoolToken(client, creator, private_key, poolToken)
optInToPoolToken(client, creator, private_key, yesToken)
optInToPoolToken(client, creator, private_key, noToken)


print("Supplying AMM with initial token")

poolTokenFirstAmount = 500_000

supply(
    client=client, 
    appID=appID, 
    q=poolTokenFirstAmount,
    supplier=creator, 
    private_key=private_key, 
    token=token, 
    poolToken=poolToken,
    yesToken=yesToken, noToken=noToken
)

print("Supplying AMM with more tokens")

poolTokenSecondAmount = 1_500_000

supply(
    client=client, 
    appID=appID, 
    q=poolTokenSecondAmount,
    supplier=creator, 
    private_key=private_key, 
    token=token, 
    poolToken=poolToken,
    yesToken=yesToken, noToken=noToken
)

print("Swapping")

yesTokenAmount = 100_000

# buy yes token
swap(
    client=client, 
    appID=appID,
    option="yes",
    q=yesTokenAmount, 
    supplier=creator, 
    private_key=private_key, 
    token=token,
    poolToken=poolToken,
    yesToken=yesToken, 
    noToken=noToken
)

#buy no token
swap(
    client=client, 
    appID=appID, 
    option="no",
    q=yesTokenAmount, 
    supplier=creator, 
    private_key=private_key, 
    token=token, 
    poolToken=poolToken,
    yesToken=yesToken,
    noToken=noToken
)

print("Withdrawing")

AllTokens = 2_000_000
#####

# pool
####
withdraw(
    client = client,
    appID = appID,
    poolTokenAmount = AllTokens, poolToken = poolToken,
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

closeAmm(
    client = client,
    appID = appID,
    closer=creator,
    private_key = private_key
)
