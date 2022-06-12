import os
from dotenv import load_dotenv
from algosdk import account
from algosdk.future import transaction
from algosdk.v2client import algod
from algosdk import mnemonic

from create_asset import create_asset
from create_amm import createAmmApp
load_dotenv()
private_key = os.getenv('key')

algod_address = "https://testnet-algorand.api.purestake.io/ps2"
algod_token = os.getenv('algod_token')
headers = {
   "X-API-Key": algod_token,
}

# initialize an algodClient
client = algod.AlgodClient(algod_token, algod_address, headers)

#create 2 tokens
# 


""" tokenA = create_asset(client, private_key)
tokenB = create_asset(client, private_key)

appID = createAmmApp(
    client=client,
    creator=creator,
    tokenA=tokenA,
    tokenB=tokenB,
    feeBps=30,
    minIncrement=1000,
) """