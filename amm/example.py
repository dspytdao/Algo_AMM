import os
from dotenv import load_dotenv
from algosdk import account
from algosdk.future import transaction
from algosdk.v2client import algod
from base64 import b64decode

from create_asset import create_asset
from create_amm import createAmmApp, setupAmmApp, optInToPoolToken, supply


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
tokenA = 95155762
tokenB = 95155770

appID = createAmmApp(
    client=client,
    creator=creator,
    private_key=private_key,
    tokenA=tokenA,
    tokenB=tokenB,
    feeBps=30,
    minIncrement=1000,
)

#https://github.com/maks-ivanov/amm-demo/blob/main/example.py
print(appID)

#appID = 95197553

print("Alice is setting up and funding amm...")
poolToken = setupAmmApp(
    client=client,
    appID=appID,
    funder=creator,
    private_key=private_key,
    tokenA=tokenA,
    tokenB=tokenB,
)
print(poolToken)
#poolToken=95197757

optInToPoolToken(client, appID, creator, private_key, poolToken)

print("Supplying AMM with initial token A and token B")

#supply(client=client, appID=appID, qA=500_000, qB=500_000, supplier=creator, private_key=private_key, tokenA=tokenA, tokenB=tokenB, poolToken=poolToken)