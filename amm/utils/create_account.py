from algosdk import account, mnemonic

# generate an account
private_key, address = account.generate_account()
print(f"Private key: {private_key}")
print(f"Address: {address}")

mnemo = mnemonic.from_private_key(private_key)
print(f"Mnemonic: \n{mnemo}")
