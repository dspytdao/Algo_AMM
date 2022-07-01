from algosdk import account
from algosdk.future import transaction

def wait_for_confirmation(client, txid):
    last_round = client.status().get("last-round")
    txinfo = client.pending_transaction_info(txid)
    while not (txinfo.get("confirmed-round") and txinfo.get("confirmed-round") > 0):
        print("Waiting for confirmation...")
        last_round += 1
        client.status_after_block(last_round)
        txinfo = client.pending_transaction_info(txid)
    print(
        "Transaction {} confirmed in round {}.".format(
            txid, txinfo.get("confirmed-round")
        )
    )
    return txinfo


def create_asset(client, private_key):
    # declare sender
    sender = account.address_from_private_key(private_key)

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
    stxn = txn.sign(private_key)

    # Send the transaction to the network and retrieve the txid.
    
    txid = client.send_transaction(stxn)
    print("Signed transaction with txID: {}".format(txid))
    # Wait for the transaction to be confirmed
    response = wait_for_confirmation(client, txid)  
    print("TXID: ", txid)
    print("Result confirmed in round: {}".format(response['confirmed-round']))
    return response['asset-index']