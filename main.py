import time
from termcolor import cprint
import random
from tqdm import tqdm
from web3 import Account
from bridge.eth_bridge import check_gas_in_eth, bridge_to_goerli
from settings import *

def load_accounts(file_path='keys.txt'):
    """Load and shuffle accounts from the keys file."""
    with open(file_path, 'r') as keys_file:
        accounts = [Account.from_key(line.strip()) for line in keys_file.readlines()]
        random.shuffle(accounts)
    return accounts

def wait_for_low_gas():
    """Wait until the gas price is below the maximum threshold."""
    while True:
        gas = check_gas_in_eth()
        if gas > MAX_GAS:
            print(f'Gas over {MAX_GAS}. Now = {gas}', end='\r')
            time.sleep(1)
        else:
            break

def bridge_wallet(account, value_transfer, network):
    """Bridge ETH for a given account."""
    cprint(f'Starting wallet: {account.address}', 'green')
    bridge_to_goerli(account, value_transfer, network=network)

def main(tr):
    """Main function to execute the bridge process across multiple accounts and cycles."""
    accounts = load_accounts()  # Load and shuffle accounts
    count = 0

    for cycle in range(1, tr + 1):  # Run for the specified number of transactions
        count += 1
        cprint(f'Starting round {count}', 'green')

        # Process each account in the shuffled list
        for number, account in enumerate(accounts, start=1):
            wait_for_low_gas()  # Wait until gas is below the threshold

            # Generate a random amount to transfer within the defined range
            value_transfer = round(random.uniform(AMOUNT_MIN, AMOUNT_MAX), 6)

            # Generate a random wait time between wallets
            wait_time_between_wallets = round(random.uniform(MIN_WAIT, MAX_WAIT))

            # Bridge ETH for this account
            bridge_wallet(account, value_transfer, network)

            # Wait between processing each wallet
            for _ in tqdm(range(wait_time_between_wallets), desc=f'Sleeping for next account {number}',
                          bar_format='{desc}: {n_fmt}/{total_fmt}'):
                time.sleep(1)

        # Sleep between cycles before the next round
        print(f"Sleeping {WAIT_BETWEEN_CYCLES} seconds for the next cycle")
        time.sleep(WAIT_BETWEEN_CYCLES)


if __name__ == '__main__':
    main(TOTAL_ROUNDS)
