from algosdk import account

# generate an account
private_key, address = account.generate_account()
print("Private key:", private_key)
print("Address:", address)