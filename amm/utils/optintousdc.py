"""opts into usdc"""

from algosdk.future import transaction

from amm.utils.setup import setup

# create (stable) asset
# token = create_asset(client, private_key)
STABLE_TOKEN = 10458941

client, creator, private_key = setup()

suggestedParams = client.suggested_params()

optInTxn = transaction.AssetOptInTxn(
    sender=creator, index=STABLE_TOKEN, sp=suggestedParams
)

signedOptInTxn = optInTxn.sign(private_key)

client.send_transaction(signedOptInTxn)
