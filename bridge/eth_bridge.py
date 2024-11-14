import json

from termcolor import cprint
from web3 import Web3
from settings import *


def initialize_web3_provider(rpc_url):
    """Initializes and returns a Web3 provider for a given RPC URL."""
    return Web3(Web3.HTTPProvider(rpc_url))


def load_abi(file_path):
    """Loads and returns an ABI from a specified JSON file."""
    with open(file_path, 'r') as abi_file:
        return json.load(abi_file)


def initialize_contract(w3, address, abi):
    """Initializes a contract object with the given Web3 provider, address, and ABI."""
    return w3.eth.contract(address=w3.to_checksum_address(address), abi=abi)


# Configurations for different networks (Arbitrum and Optimism)
network_config = {
    'arbitrum': {
        'rpc_url': ARB_RPC,
        'explorer_url': 'https://arbiscan.io/tx/',
        'bridge_address': L0_SWAPPABLE_BRIDGE_UNISWAP_V3,
        'oft_address': L0_GOERLI_ETH_TOKEN,
        'router_abi_path': 'abis/router_abi_arbi.json',
        'endpoint_abi_path': 'abis/endpoint_arbi_l0.json'
    },
    'optimism': {
        'rpc_url': OPT_RPC,
        'explorer_url': 'https://optimistic.etherscan.io/tx/',
        'bridge_address': L0_SWAPPABLE_BRIDGE_UNISWAP_V3,
        'oft_address': L0_GOERLI_ETH_TOKEN,
        'router_abi_path': 'abis/router_abi_opti.json',
        'endpoint_abi_path': 'abis/endpoint_opti_l0.json'
    }
}


def initialize_network(network):
    """Initializes Web3 provider and contract objects for the given network."""
    # Get the network configuration
    config = network_config[network]

    explorer_url = config['explorer_url']

    # Initialize Web3 provider
    w3 = initialize_web3_provider(config['rpc_url'])

    # Load ABIs
    router_abi = load_abi(config['router_abi_path'])
    endpoint_abi = load_abi(config['endpoint_abi_path'])

    # Initialize contracts
    bridge_address = w3.to_checksum_address(config['bridge_address'])
    oft_address = w3.to_checksum_address(config['oft_address'])

    bridge_contract = initialize_contract(w3, bridge_address, router_abi)
    oft_contract = initialize_contract(w3, oft_address, endpoint_abi)

    return explorer_url, w3, bridge_contract, oft_contract


# Initialize networks (Arbitrum and Optimism)
_, arbitrum_w3, t_bridge_arbitrum_router_contract, l0_arbitrum_router_contract = initialize_network('arbitrum')
_, optimism_w3, t_bridge_opti_router_contract, l0_opti_router_contract = initialize_network('optimism')



def check_gas_in_eth():
    w3 = Web3(Web3.HTTPProvider(ETH_RPC))

    gas = round(w3.eth.gas_price / 10 ** 9, 1)
    return gas


def get_balance_eth_evm_chain(network, address):
    """Fetches the ETH balance for a given address on a specified network."""
    # Initialize the network (Web3 and contracts)
    _, w3, _, _ = initialize_network(network)
    return w3.eth.get_balance(address)

def bridge_to_goerli(account, amount, network):
    """
    Bridges ETH from either Arbitrum or Optimism to Goerli.

    Args:
        account: The account object containing the address.
        amount: The amount of ETH to transfer in wei.
        network: The network to bridge from ('arbitrum' or 'optimism').
    """
    cprint(f"Bridging ETH from {network.capitalize()} to Goerli...", 'yellow')

    amount = Web3.to_wei(amount, 'ether')

    # Initialize the network (Web3 and contracts)
    explorer_url, w3, t_router_contract, router_contract = initialize_network(network)

    address = w3.to_checksum_address(account.address)
    nonce = w3.eth.get_transaction_count(address)
    gas_price = w3.eth.gas_price * GAS_PRICE_MULTI  # Increase gas price slightly
    fees = router_contract.functions.estimateSendFee(
        GOERLI_CHAIN_ID, address, amount, False, '0x'
    ).call()
    fee = fees[0]

    amount_in = amount
    amount_out_min = amount - (amount * SLIPPAGE) // 1000  # Apply slippage
    to = account.address
    refund_address = account.address
    zro_payments_address = '0x0000000000000000000000000000000000000000'
    data = '0x'

    try:
        # Build the transaction
        swap_txn = t_router_contract.functions.swapAndBridge(
            amount_in, amount_out_min, GOERLI_CHAIN_ID, to, refund_address, zro_payments_address, data
        ).build_transaction({
            'from': address,
            'value': amount_in + fee,
            'gas': 5000000,
            'gasPrice': int(gas_price),
            'nonce': nonce,
        })

        # Sign and send the transaction
        signed_swap_txn = w3.eth.account.sign_transaction(swap_txn, account.key)
        swap_txn_hash = w3.eth.send_raw_transaction(signed_swap_txn.rawTransaction)

        cprint(f"Transaction: {explorer_url}{swap_txn_hash.hex()}", 'green')
        cprint('Bridge complete', 'green')
        return swap_txn_hash
    except Exception as err:
        cprint(err, 'red')

