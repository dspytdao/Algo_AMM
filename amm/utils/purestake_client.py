"""algod client"""
from algosdk.v2client import algod
from algosdk.transaction import AssetConfigTxn


class AlgoClient:
    """algod client"""
    ALGOD_ADDRESS = "https://testnet-algorand.api.purestake.io/ps2"

    def __init__(self, algod_token):
        self.algod_token = algod_token
        self.headers = {
            "X-API-Key": algod_token,
        }
        self.client = algod.AlgodClient(
            self.algod_token, self.ALGOD_ADDRESS, self.headers)
        self.params = self.client.suggested_params()

    def wait_for_confirmation(self, tx_id):
        """
        Utility to monitor transaction confirmation.
        Args:
            tx_id: transaction id
        """
        last_round = self.client.status().get("last-round")
        tx_info = self.client.pending_transaction_info(tx_id)
        while not (tx_info.get("confirmed-round") and tx_info.get("confirmed-round") > 0):
            print("Waiting for confirmation...")
            last_round += 1
            self.client.status_after_block(last_round)
            tx_info = self.client.pending_transaction_info(tx_id)
        confirmed_round = tx_info.get("confirmed-round")
        print(f"Transaction {tx_id} confirmed in round {confirmed_round}.")
        return tx_info

    def create_asset(self, account):
        """
        Create asset.
        Args:
            account: account to sign and assign created asset
        """
        sender = account.public_key

        txn = AssetConfigTxn(
            sender=sender,
            sp=self.params,
            total=1_000_000_000,
            default_frozen=False,
            unit_name="AlgoAMM",
            asset_name="coin",
            manager=sender,
            reserve=sender,
            freeze=sender,
            clawback=sender,
            strict_empty_address_check=False,
            url=None,
            decimals=0)

        signed_txn = txn.sign(account.private_key)

        tx_id = self.client.send_transaction(signed_txn)
        print(f"Signed transaction with txID: {tx_id}")
        response = self.wait_for_confirmation(tx_id)
        print("TX ID: ", tx_id)
        confirmed_round = response['confirmed-round']
        print(f"Result confirmed in round: {confirmed_round}")
        return response['asset-index']
