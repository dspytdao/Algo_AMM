"""we manually set result of the event"""
from amm.amm_api import set_result
from amm.utils.setup import setup

client, creator, private_key = setup()

APP_ID = 100248351

set_result(
    client = client,
    app_id = APP_ID,
    second_argument = b"yes",
    funder = creator,
    private_key = private_key
)
