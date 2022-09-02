"""deploys contract"""
from algosdk.logic import get_application_address

from amm.amm_api import create_amm_app, opt_in_to_pool_token
from amm.utils.setup import setup

STABLE_TOKEN = 10458941

client, creator, private_key = setup()

opt_in_to_pool_token(client, creator, private_key, STABLE_TOKEN)

appID = create_amm_app(
    client=client,
    creator=creator,
    private_key=private_key,
    token=STABLE_TOKEN,
    min_increment=1000,
)

print(appID)

print(get_application_address(appID))
