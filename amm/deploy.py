import os
from dotenv import load_dotenv
from algosdk import account
from algosdk.v2client import algod
from algosdk.logic import get_application_address
from amm_api import createAmmApp, optInToPoolToken


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

stableToken = 10458941

optInToPoolToken(client, creator, private_key, stableToken)

appID = createAmmApp(
    client=client,
    creator=creator,
    private_key=private_key,
    token=stableToken,
    minIncrement=1000,
)

print(appID)

print(get_application_address(appID))