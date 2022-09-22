""" algod client"""
from algosdk.v2client import algod
from algosdk.future import transaction

class AlgoClient:
    """ algod client """
    ALGOD_ADDRESS = "https://testnet-algorand.api.purestake.io/ps2"

    def __init__(self, algod_token):
        self.algod_token = algod_token
        self.headers =  {
            "X-API-Key": algod_token,
        }
        self.client = algod.AlgodClient(self.algod_token, self.ALGOD_ADDRESS, self.headers)
        self.params = self.client.suggested_params()

    def wait_for_confirmation(self, txid):
        """util to monitor confirmation"""
        last_round = self.client.status().get("last-round")
        txinfo = self.client.pending_transaction_info(txid)
        while not (txinfo.get("confirmed-round") and txinfo.get("confirmed-round") > 0):
            print("Waiting for confirmation...")
            last_round += 1
            self.client.status_after_block(last_round)
            txinfo = self.client.pending_transaction_info(txid)
        confirmed_round=txinfo.get("confirmed-round")
        print(f"Transaction {txid} confirmed in round {confirmed_round}.")
        return txinfo

    def create_asset(self, account):
        """create asset"""
        sender = account.public_key

        txn = transaction.AssetConfigTxn(
            sender=sender,
            sp=self.params,
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

        txid = self.client.send_transaction(stxn)
        print(f"Signed transaction with txID: {txid}")
        # Wait for the transaction to be confirmed
        response = self.wait_for_confirmation(txid)
        print("TXID: ", txid)
        confirmed_round = response['confirmed-round']
        print(f"Result confirmed in round: {confirmed_round}")
        return response['asset-index']
