"""globals"""
from pyteal import Bytes, Int

CREATOR_KEY = Bytes("creator_key")

RESULT = Bytes("result")

TOKEN_FUNDING_KEY = Bytes("token_funding_key")
TOKEN_FUNDING_RESERVES = Bytes("token_funding_reserves")

POOL_FUNDING_RESERVES = Bytes("pool_funding_reserves")

POOL_TOKEN_KEY = Bytes("pool_token_key")
POOL_TOKENS_OUTSTANDING_KEY = Bytes("pool_tokens_outstanding_key")

YES_TOKEN_KEY = Bytes("yes_token_key")
YES_TOKENS_OUTSTANDING_KEY = Bytes("yes_tokens_outstanding_key")
YES_TOKENS_RESERVES = Bytes("yes_tokens_reserves")

NO_TOKEN_KEY = Bytes("no_token_key")
NO_TOKENS_OUTSTANDING_KEY = Bytes("no_tokens_outstanding_key")
NO_TOKENS_RESERVES = Bytes("no_tokens_reserves")

MIN_INCREMENT_KEY = Bytes("min_increment_key")

TOKEN_DEFAULT_AMOUNT = Int(10 ** 13)
