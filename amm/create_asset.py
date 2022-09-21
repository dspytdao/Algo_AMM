"""create asset"""

from algosdk.future import transaction

def wait_for_confirmation(client, txid):
    """util to monitor confirmation"""
    last_round = client.status().get("last-round")
    txinfo = client.pending_transaction_info(txid)
    while not (txinfo.get("confirmed-round") and txinfo.get("confirmed-round") > 0):
        print("Waiting for confirmation...")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(txid)
    confirmed_round=txinfo.get("confirmed-round")
    print(f"Transaction {txid} confirmed in round {confirmed_round}.")
    return txinfo


def create_asset(client, account):
    """create asset"""
    sender = account.public_key

    params = client.suggested_params()

    txn = transaction.AssetConfigTxn(
        sender=sender,
        sp=params,
        total=1_000_000_000,
        default_frozen=False,
        unit_name="Copio",
        asset_name="coin",
        manager=sender,
        reserve=sender,
        freeze=sender,
        clawback=sender,
        strict_empty_address_check=False,
        url=None,
        decimals=0)

    # Sign with secret key of creator
    stxn = txn.sign(account.private_key)

    # Send the transaction to the network and retrieve the txid.

    txid = client.send_transaction(stxn)
    print(f"Signed transaction with txID: {txid}")
    # Wait for the transaction to be confirmed
    response = wait_for_confirmation(client, txid)
    print("TXID: ", txid)
    confirmed_round = response['confirmed-round']
    print(f"Result confirmed in round: {confirmed_round}")
    return response['asset-index']
