"""we manually set result of the event"""
import os

from amm.utils.purestake_client import AlgoClient
from amm.amm_app import App
from amm.utils.account import Account

algod_token = os.getenv('algod_token')
deployer = Account(os.getenv('key'))

AlgoClient = AlgoClient(algod_token)

APP_ID = 100248351

app = App(AlgoClient.client, APP_ID)

app.set_result(
    funder=deployer,
    second_argument=b"yes",
)
