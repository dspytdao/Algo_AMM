"""deploys contract with usdc as stablecoin on testnet"""
import os

from amm.amm_app import App
from amm.utils.account import Account
from amm.utils.purestake_client import AlgoClient

STABLE_TOKEN = 10458941

algod_token = os.getenv('algod_token')
deployer = Account(os.getenv('key'))

AlgoClient = AlgoClient(algod_token)

app = App(AlgoClient.client)

appID = app.create_amm_app(
    deployer=deployer,
    token=STABLE_TOKEN,
    min_increment=1000,
)

print(appID)
