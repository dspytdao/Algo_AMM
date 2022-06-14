import os
from dotenv import load_dotenv
from algosdk import account
from algosdk.future import transaction
from algosdk.v2client import algod
from base64 import b64decode

from create_asset import create_asset
from create_amm import createAmmApp, setupAmmApp, optInToPoolToken, supply, withdraw


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

#create 2 tokens

""" tokenA = create_asset(client, private_key)
tokenB = create_asset(client, private_key)
print(f"{tokenA} and {tokenB}") """

token = 95155762

appID = createAmmApp(
    client=client,
    creator=creator,
    private_key=private_key,
    token=token,
    feeBps=30,
    minIncrement=1000,
)

#https://github.com/maks-ivanov/amm-demo/blob/main/example.py


#appID = 95328097
print(appID)

print("Alice is setting up and funding amm...")
poolToken = setupAmmApp(
    client=client,
    appID=appID,
    funder=creator,
    private_key=private_key,
    token=token,
)


#poolToken=95328119
print(poolToken)

optInToPoolToken(client, appID, creator, private_key, poolToken)

print("Supplying AMM with initial token")

poolTokenFirstAmount = 500_000

supply(client=client, appID=appID, q=poolTokenFirstAmount, supplier=creator, private_key=private_key, token=token, poolToken=poolToken)

withdraw(
    client = client,
    appID = appID,
    poolTokenAmount = poolTokenFirstAmount, poolToken = poolToken,
    withdrawAccount = creator, private_key = private_key, token = token
)