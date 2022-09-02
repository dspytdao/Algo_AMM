"""opts into usdc"""
import os
from algosdk.future import transaction
from algosdk.v2client import algod
from algosdk import account
from dotenv import load_dotenv
load_dotenv()

private_key = os.getenv('key')

creator = account.address_from_private_key(private_key)

algod_token = os.getenv('algod_token')

ALGOD_ADDRESS = "https://testnet-algorand.api.purestake.io/ps2"

headers = {
   "X-API-Key": algod_token,
}

# initialize an algodClient
client = algod.AlgodClient(algod_token, ALGOD_ADDRESS, headers)

# create (stable) asset
#token = create_asset(client, private_key)
STABLE_TOKEN = 10458941


suggestedParams = client.suggested_params()

optInTxn = transaction.AssetOptInTxn(
    sender=creator, index=STABLE_TOKEN, sp=suggestedParams
)

signedOptInTxn = optInTxn.sign(private_key)

client.send_transaction(signedOptInTxn)
