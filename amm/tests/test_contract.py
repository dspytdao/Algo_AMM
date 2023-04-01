"""tests"""
from unittest import TestCase
import os
from base64 import b64decode
from dotenv import load_dotenv

from amm.amm_app import App
from amm.utils.account import Account
from amm.utils.purestake_client import AlgoClient

load_dotenv()


class TestAmm(TestCase):
    """Class for testing lifecycle of the amm"""

    def setUp(self):
        self.algod_token = os.getenv('algod_token')
        self.deployer = Account(os.getenv('key'))
        self.algo_client = AlgoClient(self.algod_token)
        self.app = App(self.algo_client.client)

    def test_is_client(self):
        """tests environment variables and client"""
        assert isinstance(self.algod_token, str),  "Provide Algorand node key"
        assert isinstance(self.deployer.private_key,
                          str),  "Provide deployer private key"

    def test_create_amm(self):
        """tests amm"""
        stable_token = self.algo_client.create_asset(self.deployer)
        assert isinstance(
            stable_token, int), "Provide sufficient algo to deployer"

        app_id = self.app.create_amm_app(
            token=stable_token,
            min_increment=1000,
            deployer=self.deployer
        )

        assert isinstance(app_id, int), "Provide sufficient algo to deployer"

        pool_tokens = self.app.setup_amm_app(
            funder=self.deployer
        )
        pool_token = pool_tokens['pool_token_key']
        yes_token = pool_tokens['yes_token_key']
        no_token = pool_tokens['no_token_key']

        assert isinstance(pool_token, int), "failed to create pool token"
        assert isinstance(yes_token, int), "failed to create yes token"
        assert isinstance(no_token, int), "failed to create no token"

        self.app.opt_in_to_pool_token(self.deployer)
        self.app.opt_in_to_yes_token(self.deployer)
        self.app.opt_in_to_no_token(self.deployer)

        pool_token_amount = 2_000_000

        self.app.supply(
            quantity=pool_token_amount,
            supplier=self.deployer,
        )

        swap_token_amount = 100_000
        self.app.swap(
            option="yes",
            quantity=swap_token_amount,
            supplier=self.deployer
        )

        self.app.swap(
            option="no",
            quantity=swap_token_amount,
            supplier=self.deployer
        )

        self.app.set_result(
            second_argument=b"yes",
            funder=self.deployer
        )

        app = self.algo_client.client.application_info(app_id)

        glob_state = app['params']['global-state']

        ids = {}
        key = ""
        for i, _ in enumerate(glob_state):
            key = b64decode(glob_state[i]['key']).decode("utf-8")
            if glob_state[i]['value']['uint'] != 0:
                ids[key] = glob_state[i]['value']['uint']
            else:
                ids[key] = glob_state[i]['value']['bytes']

        print(ids)

        yes_token_amount = 83_333

        self.app.redeem(
            token_in=yes_token,
            token_amount=yes_token_amount,
            withdrawal_account=self.deployer,
            token_out=stable_token
        )

        self.app.withdraw(
            pool_token_amount=pool_token_amount, withdrawal_account=self.deployer
        )

        self.app.close_amm(
            closing_account=self.deployer
        )
