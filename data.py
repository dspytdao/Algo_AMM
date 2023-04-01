""" example of the contract lifetime """
import os
import json
from dotenv import load_dotenv
from algosdk.v2client.indexer import IndexerClient

from amm.utils.account import Account
from amm.utils.purestake_client import AlgoClient

load_dotenv()

algod_token = os.getenv('algod_token')
deployer = Account(os.getenv('key'))
TOKENS = [170350514, 170350518, 170350516]

algod_header = {
    'User-Agent': 'Minimal-PyTeal-SDK-Demo/0.1',
    'X-API-Key': algod_token
}

INDEXER_ADDRESS = "https://testnet-algorand.api.purestake.io/idx2"

algod_indexer = IndexerClient(
    algod_token,
    INDEXER_ADDRESS,
    algod_header
)

AlgoClient = AlgoClient(algod_token).client
last_round = AlgoClient.status()['last-round']


for token_id in TOKENS:
    data = algod_indexer.search_transactions(
        asset_id=token_id, limit=10000)
    file = json.dumps(data['transactions'])

    with open(f'json_data_{token_id}.json', 'w', encoding="utf8") as outfile:
        outfile.write(file)
