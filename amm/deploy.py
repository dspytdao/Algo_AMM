"""deploys contract"""
import os
from dotenv import load_dotenv
from algosdk import account
from algosdk.v2client import algod
from algosdk.logic import get_application_address

from amm.amm_api import create_amm_app, opt_in_to_pool_token


load_dotenv()

private_key = os.getenv('key')
creator = account.address_from_private_key(private_key)

algod_token = os.getenv('algod_token')

ALGOD_ADDRESS = "https://testnet-algorand.api.purestake.io/ps2"

headers = {
   "X-API-Key": algod_token,
}

client = algod.AlgodClient(algod_token, ALGOD_ADDRESS, headers)

STABLE_TOKEN = 10458941

opt_in_to_pool_token(client, creator, private_key, STABLE_TOKEN)

appID = create_amm_app(
    client=client,
    creator=creator,
    private_key=private_key,
    token=STABLE_TOKEN,
    min_increment=1000,
)

print(appID)

print(get_application_address(appID))
