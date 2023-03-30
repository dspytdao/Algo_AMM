"""creates client and account"""
from algosdk import account, mnemonic


class Account:
    """user account"""

    def __init__(self, private_key=''):
        self.private_key = private_key
        self.public_key = account.address_from_private_key(private_key)

    def get_mnemonic(self):
        """returns mnemonic"""
        return mnemonic.from_private_key(self.private_key)

    @staticmethod
    def generate_account():
        """generates account"""
        return account.generate_account()
