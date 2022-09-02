"""we manually set result of the event"""

import os
from dotenv import load_dotenv
from algosdk import account
from algosdk.v2client import algod

from amm_api import set_result

load_dotenv()

private_key = os.getenv('key')
creator = account.address_from_private_key(private_key)

algod_token = os.getenv('algod_token')
ALGOD_ADDRESS = "https://testnet-algorand.api.purestake.io/ps2"
headers = {
   "X-API-Key": algod_token,
}

client = algod.AlgodClient(algod_token, ALGOD_ADDRESS, headers)

APP_ID= 100248351

set_result(
    client = client,
    APP_ID= APP_ID,
    second_argument=b"yes",
    funder=creator,
    private_key = private_key
)
