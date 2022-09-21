"""opts into usdc"""

from algosdk.future import transaction

from amm.utils.setup import setup

STABLE_TOKEN = 10458941

client, creator = setup()

suggestedParams = client.suggested_params()

optInTxn = transaction.AssetOptInTxn(
    sender=creator, index=STABLE_TOKEN, sp=suggestedParams
)

signedOptInTxn = optInTxn.sign(creator.private_key)

client.send_transaction(signedOptInTxn)
