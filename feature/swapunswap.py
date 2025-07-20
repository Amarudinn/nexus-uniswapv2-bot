import os
import random
import time
from web3 import Web3
from dotenv import load_dotenv

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
WETH_ADDRESS = "0xfAdf8E61BE6e95790d627057251AA41258a207d0"

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

uniswap_v2_router_abi = '''
[
    {
        "inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type":"uint256"}
        ],
        "name": "swapExactTokensForETH",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type":"uint256[]"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [
            {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]
'''

erc20_abi = '''
[
    {
        "constant": true,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": false,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    }
]
'''

uniswap_router = web3.eth.contract(address=Web3.to_checksum_address(UNISWAP_V2_ROUTER_ADDRESS), abi=uniswap_v2_router_abi)

def get_token_contract(token_address):
    return web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=erc20_abi)

def get_token_balance(account_address, token_address):
    token_contract = get_token_contract(token_address)
    return token_contract.functions.balanceOf(account_address).call()

def approve_token(account, private_key, token_address, router_address, amount_to_approve):
    token_contract = get_token_contract(token_address)
    gas_price = web3.eth.gas_price

    while True:
        try:
            nonce = web3.eth.get_transaction_count(account.address, "pending")
            print(f"  {Colors.YELLOW}⏳ Approving {web3.from_wei(amount_to_approve, 'ether')} token for Uniswap router...{Colors.RESET}")

            transaction = token_contract.functions.approve(
                router_address,
                amount_to_approve
            ).build_transaction({
                'from': account.address,
                'gas': 120000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': CHAIN_ID
            })

            signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"  {Colors.GREEN}✅ {Colors.BOLD}Approval transaction sent{Colors.RESET}{Colors.GREEN}: {web3.to_hex(tx_hash)}{Colors.RESET}")
            web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            print(f"{Colors.GREEN}  🎉 Approval confirmed successfully!{Colors.RESET}")
            return True

        except Exception as e:
            if 'replacement transaction underpriced' in str(e) or 'nonce too low' in str(e):
                gas_price += web3.to_wei(2, 'gwei')
                print(f"  {Colors.YELLOW}⚠️ Gas price too low or nonce issue for approval, increasing to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            elif 'out of gas' in str(e):
                gas_price += web3.to_wei(5, 'gwei')
                print(f"  {Colors.RED}🔥 Approval transaction ran out of gas, increasing gas price to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            else:
                print(f"  {Colors.RED}❌ An error occurred during approval: {e}{Colors.RESET}")
                return False

def swap_eth_for_tokens(account, private_key, amount_in_wei, amount_out_min, deadline, token_address_to_swap):
    path = [web3.to_checksum_address(WETH_ADDRESS),
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
                'gas': 220000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': CHAIN_ID
            })

            signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"  {Colors.GREEN}✅ {Colors.BOLD}NEX swap transaction sent{Colors.RESET}{Colors.GREEN} https://testnet3.explorer.nexus.xyz/tx/{web3.to_hex(tx_hash)}{Colors.RESET}")
            web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            print(f"{Colors.GREEN}  🎉 NEX to {SELECTED_TOKEN_NAME} swap confirmed!{Colors.RESET}")
            return web3.to_hex(tx_hash)

        except Exception as e:
            if 'replacement transaction underpriced' in str(e) or 'nonce too low' in str(e):
                gas_price += web3.to_wei(2, 'gwei')
                print(f"  {Colors.YELLOW}⚠️ Gas price too low or nonce issue, increasing to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            elif 'out of gas' in str(e):
                gas_price += web3.to_wei(5, 'gwei')
                print(f"  {Colors.RED}🔥 Transaction ran out of gas, increasing gas price to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            else:
                print(f"  {Colors.RED}❌ An error occurred during NEX to token swap: {e}{Colors.RESET}")
                raise

def swap_tokens_for_eth(account, private_key, amount_in_token_wei, amount_out_min_eth, deadline, token_address_to_swap):
    path = [web3.to_checksum_address(token_address_to_swap), web3.to_checksum_address(WETH_ADDRESS)]

    gas_price = web3.eth.gas_price

    while True:
        try:
            nonce = web3.eth.get_transaction_count(account.address, "pending")

            transaction = uniswap_router.functions.swapExactTokensForETH(
                amount_in_token_wei,
                amount_out_min_eth,
                path,
                account.address,
                deadline
            ).build_transaction({
                'from': account.address,
                'value': 0,
                'gas': 270000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': CHAIN_ID
            })

            signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"  {Colors.GREEN}✅ {Colors.BOLD}Token unswap transaction sent{Colors.RESET}{Colors.GREEN} https://testnet3.explorer.nexus.xyz/tx/{web3.to_hex(tx_hash)}{Colors.RESET}")
            web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            print(f"{Colors.GREEN}  🎉 {SELECTED_TOKEN_NAME} to NEX unswap confirmed!{Colors.RESET}")
            return web3.to_hex(tx_hash)

        except Exception as e:
            if 'replacement transaction underpriced' in str(e) or 'nonce too low' in str(e):
                gas_price += web3.to_wei(2, 'gwei')
                print(f"  {Colors.YELLOW}⚠️ Gas price too low or nonce issue, increasing to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            elif 'out of gas' in str(e):
                gas_price += web3.to_wei(5, 'gwei')
                print(f"  {Colors.RED}🔥 Transaction ran out of gas, increasing gas price to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            else:
                print(f"  {Colors.RED}❌ An error occurred during token to NEX swap: {e}{Colors.RESET}")
                raise

def has_sufficient_eth_balance(account, amount_in_wei):
    balance = web3.eth.get_balance(account.address)
    return balance >= amount_in_wei

if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.MAGENTA}--- 🔄 Nexswap Swap & Unswap Cycle 🔄 ---{Colors.RESET}")

    min_eth = 0.0
    max_eth = 0.0
    try:
        min_eth = float(input(f"{Colors.CYAN}Enter minimum NEX amount for initial swap (e.g., 0.1): {Colors.RESET}"))
        max_eth = float(input(f"{Colors.CYAN}Enter maximum NEX amount for initial swap (e.g., 0.5): {Colors.RESET}"))
        if min_eth <= 0 or max_eth <= 0 or min_eth > max_eth:
            raise ValueError("Invalid NEX range. Ensure positive values and minimum less than or equal to maximum.")
    except ValueError as e:
        print(f"{Colors.RED}Error: {e}{Colors.RESET}")
        exit()

    print(f"\n{Colors.BOLD}{Colors.BLUE}--- Select Target Token for Swap (NEX to Token) ---{Colors.RESET}")
    token_names = list(AVAILABLE_TOKENS.keys())
    for i, token_name in enumerate(token_names):
        print(f"{Colors.WHITE}{i+1}. {token_name} ({AVAILABLE_TOKENS[token_name]}){Colors.RESET}")

    while True:
        try:
            choice = int(input(f"{Colors.CYAN}Enter the number of the token you want to swap to: {Colors.RESET}"))
            if 1 <= choice <= len(token_names):
                SELECTED_TOKEN_NAME = token_names[choice - 1]
                TOKEN_ADDRESS = AVAILABLE_TOKENS[SELECTED_TOKEN_NAME]
                print(f"{Colors.GREEN}✅ You selected: {Colors.BOLD}{SELECTED_TOKEN_NAME}{Colors.RESET}")
                break
            else:
                print(f"{Colors.RED}Invalid choice. Please enter a valid number.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Invalid input. Please enter a number.{Colors.RESET}")

    unswap_percentage = 0.0
    while True:
        try:
            percent_input = float(input(f"{Colors.CYAN}\nEnter the percentage of {SELECTED_TOKEN_NAME} to unswap back to NEX (e.g., 50 for 50%): {Colors.RESET}"))
            if 0 <= percent_input <= 100:
                unswap_percentage = percent_input / 100.0
                print(f"{Colors.GREEN}✅ You chose to unswap {Colors.BOLD}{percent_input:.2f}%{Colors.RESET}{Colors.GREEN} of the received tokens.{Colors.RESET}")
                break
            else:
                print(f"{Colors.RED}Invalid percentage. Please enter a value between 0 and 100.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Invalid input. Please enter a number.{Colors.RESET}")

    run_in_loop = False
    while True:
        loop_choice = input(f"{Colors.CYAN}Do you want to run the swap & unswap cycle continuously? (yes/no): {Colors.RESET}").lower().strip()
        if loop_choice in ['yes', 'y']:
            run_in_loop = True
            print(f"{Colors.GREEN}✅ Loop mode activated. Swap & unswap cycle will run continuously.{Colors.RESET}")
            break
        elif loop_choice in ['no', 'n']:
            run_in_loop = False
            print(f"{Colors.GREEN}✅ Single execution mode. Swap & unswap cycle will run once for each account.{Colors.RESET}")
            break
        else:
            print(f"{Colors.RED}Invalid choice. Please enter 'yes' or 'no'.{Colors.RESET}")

    amount_out_min = 0
    amount_out_min_eth = 0

    deadline = int(web3.eth.get_block('latest').timestamp) + 300

    accounts = [web3.eth.account.from_key(pk) for pk in PRIVATE_KEYS]
    account_index = 0

    print(f"\n{Colors.BOLD}{Colors.MAGENTA}--- Starting Swap & Unswap Cycle ---{Colors.RESET}")

    max_retries_per_operation = 3
    current_operation_retries = 0

    loop_condition = True if run_in_loop else False
    while loop_condition or (not run_in_loop and account_index < len(accounts)):
        try:
            current_account = accounts[account_index]
            current_private_key = PRIVATE_KEYS[account_index]

            print(f"\n{Colors.BOLD}{Colors.BLUE}====================================================={Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.BLUE}--- ACTIVE ACCOUNT: {current_account.address} ---{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.BLUE}====================================================={Colors.RESET}")

            # --- NEX TO TOKEN SWAP ---
            print(f"\n{Colors.BOLD}{Colors.CYAN}--- Initiating NEX to Token SWAP ---{Colors.RESET}")
            eth_amount = round(random.uniform(min_eth, max_eth), 4)
            amount_in_wei = web3.to_wei(eth_amount, 'ether')

            print(f"{Colors.WHITE}🔄 Attempting to swap {Colors.BOLD}{eth_amount} NEX{Colors.RESET}{Colors.WHITE} for {SELECTED_TOKEN_NAME}...{Colors.RESET}")

            if not has_sufficient_eth_balance(current_account, amount_in_wei):
                current_eth_balance = web3.from_wei(web3.eth.get_balance(current_account.address), 'ether')
                print(f"  {Colors.RED}❌ {Colors.BOLD}Insufficient NEX balance for account {current_account.address}{Colors.RESET}{Colors.RED}. Balance: {current_eth_balance} NEX. Skipping swap.{Colors.RESET}")
                current_operation_retries = 0
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(1)
                continue

            estimated_token_received_wei = 0
            try:
                swap_path_eth_to_token = [web3.to_checksum_address(WETH_ADDRESS), web3.to_checksum_address(TOKEN_ADDRESS)]
                estimated_amounts = uniswap_router.functions.getAmountsOut(amount_in_wei, swap_path_eth_to_token).call()
                estimated_token_received_wei = estimated_amounts[1]
                print(f"   {Colors.CYAN}Estimated {SELECTED_TOKEN_NAME} to receive: {web3.from_wei(estimated_token_received_wei, 'ether')} {SELECTED_TOKEN_NAME}{Colors.RESET}")
            except Exception as e:
                print(f"  {Colors.RED}❌ Failed to get estimated token amount: {e}. Skipping swap.{Colors.RESET}")
                current_operation_retries = 0
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(1)
                continue

            try:
                swap_eth_for_tokens(current_account, current_private_key, amount_in_wei, amount_out_min, deadline, TOKEN_ADDRESS)
            except Exception as e:
                print(f"  {Colors.RED}❌ NEX to {SELECTED_TOKEN_NAME} swap failed: {e}. Skipping unswap.{Colors.RESET}")
                current_operation_retries = 0
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(5)
                continue

            delay = random.randint(5, 10)
            print(f"{Colors.YELLOW}😴 Waiting {delay} seconds after SWAP...{Colors.RESET}")
            time.sleep(delay)

            # --- TOKEN TO NEX UNSWAP ---
            print(f"\n{Colors.BOLD}{Colors.CYAN}--- Initiating Token to NEX UNSWAP ---{Colors.RESET}")
            if unswap_percentage > 0 and estimated_token_received_wei > 0:
                unswap_token_amount_wei = int(estimated_token_received_wei * unswap_percentage)
                unswap_token_amount = web3.from_wei(unswap_token_amount_wei, 'ether')

                print(f"{Colors.WHITE}🔄 Attempting to unswap {Colors.BOLD}{unswap_token_amount} {SELECTED_TOKEN_NAME}{Colors.RESET}{Colors.WHITE} ({unswap_percentage*100:.2f}%) back to NEX...{Colors.RESET}")

                current_token_balance_wei_after_swap = get_token_balance(current_account.address, TOKEN_ADDRESS)
                current_token_balance_after_swap = web3.from_wei(current_token_balance_wei_after_swap, 'ether')

                if current_token_balance_wei_after_swap < unswap_token_amount_wei:
                    print(f"  {Colors.RED}❌ Insufficient {SELECTED_TOKEN_NAME} balance for unswap. Balance: {current_token_balance_after_swap} {SELECTED_TOKEN_NAME}. Skipping unswap.{Colors.RESET}")
                else:
                    if not approve_token(current_account, current_private_key, TOKEN_ADDRESS, UNISWAP_V2_ROUTER_ADDRESS, unswap_token_amount_wei):
                        print(f"  {Colors.RED}❌ Failed to approve token for unswap. Skipping unswap.{Colors.RESET}")
                    else:
                        try:
                            swap_tokens_for_eth(current_account, current_private_key, unswap_token_amount_wei, amount_out_min_eth, deadline, TOKEN_ADDRESS)
                        except Exception as e:
                            print(f"  {Colors.RED}❌ {SELECTED_TOKEN_NAME} to NEX unswap failed: {e}.{Colors.RESET}")
            else:
                print(f"  {Colors.CYAN}ℹ️ No unswap performed as percentage is 0% or estimated tokens received were 0.{Colors.RESET}")

            delay = random.randint(5, 10)
            print(f"{Colors.YELLOW}😴 Waiting {delay} seconds after UNSWAP...{Colors.RESET}")
            time.sleep(delay)

            current_operation_retries = 0
            account_index = (account_index + 1) % len(accounts)
            if not run_in_loop and account_index == 0:
                break

        except Exception as e:
            error_message = str(e)
            print(f"\n{Colors.RED}❌ An unexpected error occurred in the cycle for account {current_account.address}: {error_message}{Colors.RESET}")

            if "Could not transact with/call contract function, is contract deployed correctly and chain synced?" in error_message and current_operation_retries < max_retries_per_operation:
                current_operation_retries += 1
                print(f"{Colors.YELLOW}⚠️ Retrying operation for {current_account.address} ({current_operation_retries}/{max_retries_per_operation} retries)...{Colors.RESET}")
                time.sleep(5)
                continue
            else:
                current_operation_retries = 0
                print(f"{Colors.YELLOW}  Moving to the next account after a brief pause...{Colors.RESET}")
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(5)

    print(f"\n{Colors.BOLD}{Colors.MAGENTA}--- All swap & unswap cycles completed. ---{Colors.RESET}")