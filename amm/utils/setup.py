"""creates client and account"""

import os
from dotenv import load_dotenv
from algosdk.v2client import algod
from algosdk import account

load_dotenv()

private_key = os.getenv('key')
algod_token = os.getenv('algod_token')

ALGOD_ADDRESS = "https://testnet-algorand.api.purestake.io/ps2"

headers = {
   "X-API-Key": algod_token,
}

def setup():
    """sets up algod client and account"""
    client = algod.AlgodClient(algod_token, ALGOD_ADDRESS, headers)
    creator = account.address_from_private_key(private_key)
    return client, creator, private_key
