import os
import random
import time
from web3 import Web3
from dotenv import load_dotenv
from colorama import Fore

class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

load_dotenv()

PRIVATE_KEYS = os.getenv("PRIVATE_KEYS").split(",")
if not PRIVATE_KEYS:
    raise ValueError(f"{Colors.RED}Private keys not found in .env file{Colors.RESET}")

RPC_URL = "https://testnet3.rpc.nexus.xyz"
CHAIN_ID = 3940

UNISWAP_V2_ROUTER_ADDRESS = "0x32aA9448586b06d2d42Fe4CFabF1c7AcD03bAE31"

AVAILABLE_TOKENS = {
    "NXS": "0x3eC55271351865ab99a9Ce92272C3E908f2E627b",
    "NEXI": "0x184eE44cF8B7Fec2371dc46D9076fFB2c1E0Ce65",
    "AIE": "0xF6f61565947621387ADF3BeD7ba02533aB013CCd"
}

TOKEN_ADDRESS = ""
SELECTED_TOKEN_NAME = ""

web3 = Web3(Web3.HTTPProvider(RPC_URL))
if not web3.is_connected():
    raise ConnectionError(f"{Colors.RED}Failed to connect to RPC URL{Colors.RESET}")

uniswap_v2_router_abi = '[{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"}]'

uniswap_router = web3.eth.contract(address=Web3.to_checksum_address(UNISWAP_V2_ROUTER_ADDRESS), abi=uniswap_v2_router_abi)

def swap_eth_for_tokens(account, private_key, amount_in_wei, amount_out_min, deadline, token_address_to_swap):
    path = [web3.to_checksum_address("0xfAdf8E61BE6e95790d627057251AA41258a207d0"),
            web3.to_checksum_address(token_address_to_swap)]

    gas_price = web3.eth.gas_price

    while True:
        try:
            nonce = web3.eth.get_transaction_count(account.address, "pending")

            transaction = uniswap_router.functions.swapExactETHForTokens(
                amount_out_min,
                path,
                account.address,
                deadline
            ).build_transaction({
                'from': account.address,
                'value': amount_in_wei,
                'gas': 200000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': CHAIN_ID
            })

            signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)

            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"  {Colors.GREEN}✅ {Colors.BOLD}Transaction sent{Colors.RESET}")
            return web3.to_hex(tx_hash)

        except Exception as e:
            if 'replacement transaction underpriced' in str(e) or 'nonce too low' in str(e):
                gas_price += web3.to_wei(2, 'gwei')
                print(f"  {Colors.YELLOW}⚠️ Gas price too low or nonce issue, increasing to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            elif 'out of gas' in str(e):
                gas_price += web3.to_wei(5, 'gwei')
                print(f"  {Colors.RED}🔥 Transaction ran out of gas, increasing gas price to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            else:
                print(f"  {Colors.RED}❌ An error occurred during transaction: {e}{Colors.RESET}")
                raise

if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.MAGENTA}--- 🚀 Nexswap NEX to Token Swapper 🚀 ---{Colors.RESET}")

    min_eth = 0.0
    max_eth = 0.0
    try:
        min_eth = float(input(f"{Colors.CYAN}Enter the minimum NEX amount to swap (e.g., 0.1): {Colors.RESET}"))
        max_eth = float(input(f"{Colors.CYAN}Enter the maximum NEX amount to swap (e.g., 0.5): {Colors.RESET}"))
        if min_eth <= 0 or max_eth <= 0 or min_eth > max_eth:
            raise ValueError("Invalid NEX range. Ensure positive values and minimum less than or equal to maximum.")
    except ValueError as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        exit()

    print(f"\n{Colors.BOLD}{Colors.BLUE}--- Select Token to Swap ---{Colors.RESET}")
    token_names = list(AVAILABLE_TOKENS.keys())
    for i, token_name in enumerate(token_names):
        print(f"{Colors.WHITE}{i+1}. {token_name} ({AVAILABLE_TOKENS[token_name]}){Colors.RESET}")

    while True:
        try:
            choice = int(input(f"{Colors.CYAN}Enter the number of the token you want to swap: {Colors.RESET}"))
            if 1 <= choice <= len(token_names):
                SELECTED_TOKEN_NAME = token_names[choice - 1]
                TOKEN_ADDRESS = AVAILABLE_TOKENS[SELECTED_TOKEN_NAME]
                print(f"{Colors.GREEN}✅ You selected: {Colors.BOLD}{SELECTED_TOKEN_NAME}{Colors.RESET}")
                break
            else:
                print(f"{Colors.RED}Invalid choice. Please enter a valid number.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Invalid input. Please enter a number.{Colors.RESET}")

    run_in_loop = False
    while True:
        loop_choice = input(f"{Colors.CYAN}Do you want to run the swap in a continuous loop? (yes/no): {Colors.RESET}").lower().strip()
        if loop_choice in ['yes', 'y']:
            run_in_loop = True
            print(f"{Colors.GREEN}✅ Loop mode activated. Swaps will run continuously.{Colors.RESET}")
            break
        elif loop_choice in ['no', 'n']:
            run_in_loop = False
            print(f"{Colors.GREEN}✅ Single execution mode. Swaps will run once for each account.{Colors.RESET}")
            break
        else:
            print(f"{Colors.RED}Invalid choice. Please enter 'yes' or 'no'.{Colors.RESET}")

    amount_out_min = 0

    deadline = int(web3.eth.get_block('latest').timestamp) + 300

    accounts = [web3.eth.account.from_key(pk) for pk in PRIVATE_KEYS]
    account_index = 0

    def has_sufficient_balance(account, amount_in_wei):
        balance = web3.eth.get_balance(account.address)
        return balance >= amount_in_wei

    print(f"\n{Colors.BOLD}{Colors.MAGENTA}--- Starting Swap Operations ---{Colors.RESET}")

    if run_in_loop:
        while True:
            try:
                current_account = accounts[account_index]
                current_private_key = PRIVATE_KEYS[account_index]

                eth_amount = round(random.uniform(min_eth, max_eth), 4)
                amount_in_wei = web3.to_wei(eth_amount, 'ether')

                print(f"\n{Colors.WHITE}🔄 {Colors.BOLD}Preparing swap for account:{Colors.RESET}{Colors.WHITE} {current_account.address}{Colors.RESET}")
                print(f"{Colors.WHITE}   Attempting to swap {Colors.BOLD}{eth_amount} NEX{Colors.RESET}{Colors.WHITE} for {SELECTED_TOKEN_NAME}...{Colors.RESET}")

                if not has_sufficient_balance(current_account, amount_in_wei):
                    current_balance = web3.from_wei(web3.eth.get_balance(current_account.address), 'ether')
                    print(f"  {Colors.RED}❌ {Colors.BOLD}Insufficient balance for account {current_account.address}{Colors.RESET}{Colors.RED}. Balance: {current_balance} NEX. Skipping to next account.{Colors.RESET}")
                    account_index = (account_index + 1) % len(accounts)
                    time.sleep(1)
                    continue

                tx_hash = swap_eth_for_tokens(current_account, current_private_key, amount_in_wei, amount_out_min, deadline, TOKEN_ADDRESS)
                print(f"{Colors.GREEN}  🎉 {Colors.BOLD}Swap successful for {eth_amount} NEX{Colors.RESET}{Colors.GREEN} https://testnet3.explorer.nexus.xyz/tx/{tx_hash}{Colors.RESET}")

                delay = random.randint(5, 15)
                print(f"{Colors.YELLOW}  😴 Waiting for {delay} seconds before next transaction...{Colors.RESET}")
                time.sleep(delay)

                account_index = (account_index + 1) % len(accounts)

            except Exception as e:
                print(f"  {Colors.RED}❌ An unexpected error occurred during swapping for account {accounts[account_index].address}: {e}{Colors.RESET}")
                print(f"{Colors.YELLOW}  Moving to the next account after a brief pause...{Colors.RESET}")
                account_index = (account_index + 1) % len(accounts)
                time.sleep(5)
    else:
        for i in range(len(accounts)):
            try:
                current_account = accounts[account_index]
                current_private_key = PRIVATE_KEYS[account_index]

                eth_amount = round(random.uniform(min_eth, max_eth), 4)
                amount_in_wei = web3.to_wei(eth_amount, 'ether')

                print(f"\n{Colors.WHITE}🔄 {Colors.BOLD}Preparing swap for account:{Colors.RESET}{Colors.WHITE} {current_account.address}{Colors.RESET}")
                print(f"{Colors.WHITE}   Attempting to swap {Colors.BOLD}{eth_amount} NEX{Colors.RESET}{Colors.WHITE} for {SELECTED_TOKEN_NAME}...{Colors.RESET}")

                if not has_sufficient_balance(current_account, amount_in_wei):
                    current_balance = web3.from_wei(web3.eth.get_balance(current_account.address), 'ether')
                    print(f"  {Colors.RED}❌ {Colors.BOLD}Insufficient balance for account {current_account.address}{Colors.RESET}{Colors.RED}. Balance: {current_balance} NEX. Skipping to next account.{Colors.RESET}")
                    account_index = (account_index + 1) % len(accounts)
                    time.sleep(1)
                    continue

                tx_hash = swap_eth_for_tokens(current_account, current_private_key, amount_in_wei, amount_out_min, deadline, TOKEN_ADDRESS)
                print(f"{Colors.GREEN}  🎉 {Colors.BOLD}Swap successful for {eth_amount} NEX{Colors.RESET}{Colors.GREEN} https://testnet3.explorer.nexus.xyz/tx/{tx_hash}{Colors.RESET}")

                if i < len(accounts) - 1:
                    delay = random.randint(5, 15)
                    print(f"{Colors.YELLOW}  😴 Waiting for {delay} seconds before next transaction...{Colors.RESET}")
                    time.sleep(delay)

                account_index = (account_index + 1) % len(accounts)

            except Exception as e:
                print(f"  {Colors.RED}❌ An unexpected error occurred during swapping for account {accounts[account_index].address}: {e}{Colors.RESET}")
                print(f"{Colors.YELLOW}  Moving to the next account after a brief pause...{Colors.RESET}")
                account_index = (account_index + 1) % len(accounts)
                time.sleep(5)
        print(f"\n{Colors.BOLD}{Colors.MAGENTA}--- All single execution swaps completed. ---{Colors.RESET}")