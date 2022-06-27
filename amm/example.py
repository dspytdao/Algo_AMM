import os
from dotenv import load_dotenv
from algosdk import account
from algosdk.v2client import algod

from create_asset import create_asset
from amm_api import createAmmApp, setupAmmApp, optInToPoolToken, \
    supply, withdraw, swap


load_dotenv()

private_key = os.getenv('key')
creator = account.address_from_private_key(private_key)


algod_address = "https://testnet-algorand.api.purestake.io/ps2"
algod_token = os.getenv('algod_token')
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
    feeBps=30,
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
# redemption for for yes/no
# pool, reaching the deadline
####
withdraw(
    client = client,
    appID = appID,
    poolTokenAmount = AllTokens, poolToken = poolToken,
    withdrawAccount = creator, private_key = private_key, token = token
)

