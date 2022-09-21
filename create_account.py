"""generate an account"""
from algosdk import account

private_key, address = account.generate_account()
print(f"Private key: {private_key}, Address: {address}")
