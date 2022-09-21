"""we manually set result of the event"""
from amm.amm_api import App
from amm.utils.setup import setup


APP_ID = 100248351

client, creator = setup()

app = App(client, APP_ID )

app.set_result(
    funder=creator,
    second_argument = b"yes",
)
