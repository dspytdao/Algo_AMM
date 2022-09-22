""" example of the contract lifetime """
import os
from dotenv import load_dotenv

from amm.amm_app import App
from amm.utils.account import Account
from amm.utils.purestake_client import AlgoClient

load_dotenv()

algod_token = os.getenv('algod_token')
deployer = Account(os.getenv('key'))

AlgoClient = AlgoClient(algod_token)

token = AlgoClient.create_asset(deployer)

app = App(AlgoClient.client)

appID = app.create_amm_app(
    token=token,
    min_increment=1000,
    deployer=deployer
)

print(f"Alice is setting up and funding amm {appID}")

Tokens = app.setup_amm_app(
    funder=deployer
)

poolToken = Tokens['pool_token_key']
yesToken = Tokens['yes_token_key']
noToken = Tokens['no_token_key']

print(Tokens['pool_token_key'], Tokens['yes_token_key'], Tokens['no_token_key'])

app.opt_in_to_pool_token(deployer)
app.opt_in_to_yes_token(deployer)
app.opt_in_to_no_token(deployer)

print("Supplying AMM with initial token")

POOL_TOKEN_FIRST_AMOUNT = 500_000

app.supply(
    quantity=POOL_TOKEN_FIRST_AMOUNT,
    supplier=deployer,
)

print("Supplying AMM with more tokens")

POOL_TOKEN_SECOND_AMOUNT = 1_500_000

app.supply(
    quantity=POOL_TOKEN_SECOND_AMOUNT,
    supplier=deployer,
)

print("Swapping")

YES_TOKEN_AMOUNT = 100_000

# buy yes token
app.swap(
    option="yes",
    quantity=YES_TOKEN_AMOUNT,
    supplier=deployer
)

#buy no token
app.swap(
    option="no",
    quantity=YES_TOKEN_AMOUNT,
    supplier=deployer
)

print("Setting Result")

app.set_result(
    second_argument=b"yes",
    funder=deployer
)

print("Redeeming")

YES_TOKENS_AMOUNT = 83_333

app.redeem(
    token_in = yesToken,
    token_amount = YES_TOKENS_AMOUNT,
    withdrawal_account = deployer,
    token_out = token
)

print("Withdrawing")

ALL_TOKENS = 2_000_000

app.withdraw(
    pool_token_amount = ALL_TOKENS, withdrawal_account = deployer
)

print("Deleting")

app.close_amm(
    closing_account=deployer
)
