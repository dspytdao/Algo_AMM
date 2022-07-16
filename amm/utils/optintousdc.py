from algosdk.future import transaction
import os
from dotenv import load_dotenv
from algosdk import account
from algosdk.v2client import algod
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

# create (stable) asset
#token = create_asset(client, private_key)
stableToken = 10458941


suggestedParams = client.suggested_params()

optInTxn = transaction.AssetOptInTxn(
    sender=creator, index=stableToken, sp=suggestedParams
)

signedOptInTxn = optInTxn.sign(private_key)

client.send_transaction(signedOptInTxn)