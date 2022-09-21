"""creates client and account"""

import os
from dotenv import load_dotenv
from algosdk import account, mnemonic
from algosdk.v2client import algod

load_dotenv()

algod_token = os.getenv('algod_token')

ALGOD_ADDRESS = "https://testnet-algorand.api.purestake.io/ps2"

headers = {
   "X-API-Key": algod_token,
}

class Account:
    """ user account  """
    def __init__(self, private_key=''):
        self.private_key = private_key
        self.public_key  = account.address_from_private_key(private_key)

    def get_mnemonic(self):
        """ returns mnemonic"""
        return mnemonic.from_private_key(self.private_key)

    @staticmethod
    def generate_account():
        """ generates account"""
        return account.generate_account()

def setup():
    """ sets up algod client and account """
    client = algod.AlgodClient(algod_token, ALGOD_ADDRESS, headers)
    deployer = Account(os.getenv('key'))
    return client, deployer
    