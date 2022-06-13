from pyteal import Bytes, Int

CREATOR_KEY = Bytes("creator_key")
TOKEN_A_KEY = Bytes("token_a_key")
TOKEN_B_KEY = Bytes("token_b_key")
POOL_TOKEN_KEY = Bytes("pool_token_key")
FEE_BPS_KEY = Bytes("fee_bps_key")
MIN_INCREMENT_KEY = Bytes("min_increment_key")
POOL_TOKENS_OUTSTANDING_KEY = Bytes("pool_tokens_outstanding_key")
SCALING_FACTOR = Int(10 ** 13)
POOL_TOKEN_DEFAULT_AMOUNT = Int(10 ** 13)