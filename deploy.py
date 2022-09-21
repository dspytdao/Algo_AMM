"""deploys contract"""
from amm.amm_api import App
from amm.utils.setup import setup

STABLE_TOKEN = 10458941

client, creator = setup()

app = App(client)

appID = app.create_amm_app(
    deployer=creator,
    token=STABLE_TOKEN,
    min_increment=1000,
)

print(appID)
