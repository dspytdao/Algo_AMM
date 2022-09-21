"""deploys contract"""
from algosdk.logic import get_application_address

from amm.amm_api import App
from amm.utils.setup import setup

STABLE_TOKEN = 10458941

client, creator = setup()

app = App()

app.opt_in_to_pool_token(creator, STABLE_TOKEN)

appID = app.create_amm_app(
    deployer=creator,
    token=STABLE_TOKEN,
    min_increment=1000,
)

print(appID)

print(get_application_address(appID))
