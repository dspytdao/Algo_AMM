""" example of the contract lifetime """
from amm.create_asset import create_asset
from amm.amm_api import App
from amm.utils.setup import setup


client, deployer = setup()

# create (stable) asset
token = create_asset(client, deployer)

app = App(client)

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

print("Withdrawing")

ALL_TOKENS = 2_000_000

"""
withdraw(
    client = client,
    appID = appID,
    poolTokenAmount = ALL_TOKENS, poolToken = poolToken,
    withdrawAccount = creator, private_key = private_key, token = token
)

print("Result")
#set winner

set_result(
    client = client,
    appID = appID,
    second_argument=b"yes",
    funder=creator,
    private_key = private_key
)


# redemption for for yes/no

print("Redeeming")

YesTokensAmount = 95_238

redeem(
    client = client,
    appID = appID,
    TokenAmount = YesTokensAmount,
    Token = yesToken,
    withdrawAccount = creator, private_key = private_key, token = token
)

# Delete

print("Deleting")

close_amm(
    client = client,
    appID = appID,
    closer=creator,
    private_key = private_key
) """
