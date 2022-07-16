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

appID = 99887636
#set winner

set_result(
    client = client,
    appID = appID,
    second_argument=b"yes",
    funder=creator,
    private_key = private_key
)
