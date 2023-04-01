"""generate an account"""

from algosdk import account

private_key, address = account.generate_account()
print(f"Private key: {private_key}\nAddress: {address}")

FILENAME = ".env"

with open(FILENAME, "r", encoding="utf8") as file:
    string_list = file.readlines()
    file.close()

string_list[0] = f'key="{private_key}"\n'

with open(FILENAME, "w", encoding="utf8"):
    NEW_FILE = "".join(string_list)
    file.write(NEW_FILE)
    file.close()
