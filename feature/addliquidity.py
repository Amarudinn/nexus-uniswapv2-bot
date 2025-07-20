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
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "amountTokenDesired", "type": "uint256"},
            {"internalType": "uint256", "name": "amountTokenMin", "type": "uint256"},
            {"internalType": "uint256", "name": "amountETHMin", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "addLiquidityETH",
        "outputs": [
            {"internalType": "uint256", "name": "amountToken", "type": "uint256"},
            {"internalType": "uint256", "name": "amountETH", "type": "uint256"},
            {"internalType": "uint256", "name": "liquidity", "type": "uint256"}
        ],
        "stateMutability": "payable",
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
            print(f"  {Colors.YELLOW}⏳ Approving {web3.from_wei(amount_to_approve, 'ether')} {SELECTED_TOKEN_NAME} for Nexswap router...{Colors.RESET}")

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
            print(f"  {Colors.GREEN}✅ {Colors.BOLD}Approval transaction sent{Colors.RESET}")
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

def add_liquidity_eth(account, private_key, token_address, amount_token_desired, amount_eth_desired, amount_token_min, amount_eth_min, deadline):
    gas_price = web3.eth.gas_price

    while True:
        try:
            nonce = web3.eth.get_transaction_count(account.address, "pending")
            print(f"  {Colors.YELLOW}⏳ Adding liquidity for {SELECTED_TOKEN_NAME} and NEX...{Colors.RESET}")

            transaction = uniswap_router.functions.addLiquidityETH(
                web3.to_checksum_address(token_address),
                amount_token_desired,
                amount_token_min,
                amount_eth_min,
                account.address,
                deadline
            ).build_transaction({
                'from': account.address,
                'value': amount_eth_desired,
                'gas': 320000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': CHAIN_ID
            })

            signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"  {Colors.GREEN}✅ {Colors.BOLD}Add liquidity transaction sent{Colors.RESET}{Colors.GREEN} https://testnet3.explorer.nexus.xyz/tx/{web3.to_hex(tx_hash)}{Colors.RESET}")
            web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            print(f"{Colors.GREEN}  🎉 Add liquidity for {SELECTED_TOKEN_NAME}/NEX confirmed!{Colors.RESET}")
            return web3.to_hex(tx_hash)

        except Exception as e:
            if 'replacement transaction underpriced' in str(e) or 'nonce too low' in str(e):
                gas_price += web3.to_wei(2, 'gwei')
                print(f"  {Colors.YELLOW}⚠️ Gas price too low or nonce issue for add liquidity, increasing to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            elif 'out of gas' in str(e):
                gas_price += web3.to_wei(5, 'gwei')
                print(f"  {Colors.RED}🔥 Add liquidity transaction ran out of gas, increasing gas price to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            else:
                print(f"  {Colors.RED}❌ An error occurred during add liquidity: {e}{Colors.RESET}")
                raise

def has_sufficient_eth_balance(account, amount_in_wei):
    balance = web3.eth.get_balance(account.address)
    return balance >= amount_in_wei

if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.MAGENTA}--- 💧 Nexswap Liquidity Adder 💧 ---{Colors.RESET}")

    print(f"\n{Colors.BOLD}{Colors.BLUE}--- Select Token to Add Liquidity (with NEX) ---{Colors.RESET}")
    token_names = list(AVAILABLE_TOKENS.keys())
    for i, token_name in enumerate(token_names):
        print(f"{Colors.WHITE}{i+1}. {token_name} ({AVAILABLE_TOKENS[token_name]}){Colors.RESET}")

    while True:
        try:
            choice = int(input(f"{Colors.CYAN}Enter the number of the token you want to add liquidity for: {Colors.RESET}"))
            if 1 <= choice <= len(token_names):
                SELECTED_TOKEN_NAME = token_names[choice - 1]
                TOKEN_ADDRESS = AVAILABLE_TOKENS[SELECTED_TOKEN_NAME]
                print(f"{Colors.GREEN}✅ You selected: {Colors.BOLD}{SELECTED_TOKEN_NAME}{Colors.RESET}")
                break
            else:
                print(f"{Colors.RED}Invalid choice. Please enter a valid number.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Invalid input. Please enter a number.{Colors.RESET}")

    desired_token_amount = 0.0
    desired_eth_amount = 0.0

    try:
        desired_eth_amount = float(input(f"{Colors.CYAN}Enter the amount of NEX to add (e.g., 0.1): {Colors.RESET}"))
        if desired_eth_amount <= 0:
            raise ValueError("NEX amount must be positive.")
    except ValueError as e:
        print(f"{Colors.RED}Invalid input: {e}. Please enter a number.{Colors.RESET}")
        exit()

    try:
        path_eth_to_token = [web3.to_checksum_address(WETH_ADDRESS), web3.to_checksum_address(TOKEN_ADDRESS)]
        amounts_out = uniswap_router.functions.getAmountsOut(web3.to_wei(desired_eth_amount, 'ether'), path_eth_to_token).call()
        desired_token_amount = web3.from_wei(amounts_out[1], 'ether')
        print(f"   {Colors.CYAN}Approximately {Colors.BOLD}{desired_token_amount:.4f} {SELECTED_TOKEN_NAME}{Colors.RESET}{Colors.CYAN} needed for {desired_eth_amount} NEX at current ratio.{Colors.RESET}")
    except Exception as e:
        print(f"  {Colors.RED}❌ Failed to calculate required {SELECTED_TOKEN_NAME}: {e}. Ensure pool has liquidity.{Colors.RESET}")
        exit()

    run_in_loop = False
    while True:
        loop_choice = input(f"{Colors.CYAN}Do you want to run liquidity addition in a continuous loop? (yes/no): {Colors.RESET}").lower().strip()
        if loop_choice in ['yes', 'y']:
            run_in_loop = True
            print(f"{Colors.GREEN}✅ Loop mode activated. Liquidity addition will run continuously.{Colors.RESET}")
            break
        elif loop_choice in ['no', 'n']:
            run_in_loop = False
            print(f"{Colors.GREEN}✅ Single execution mode. Liquidity addition will run once for each account.{Colors.RESET}")
            break
        else:
            print(f"{Colors.RED}Invalid choice. Please enter 'yes' or 'no'.{Colors.RESET}")

    slippage_tolerance_percent = 0.5

    deadline = int(web3.eth.get_block('latest').timestamp) + 300

    accounts = [web3.eth.account.from_key(pk) for pk in PRIVATE_KEYS]
    account_index = 0

    print(f"\n{Colors.BOLD}{Colors.MAGENTA}--- Starting Liquidity Addition Operations ---{Colors.RESET}")

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

            amount_token_desired_wei = web3.to_wei(desired_token_amount, 'ether')
            amount_eth_desired_wei = web3.to_wei(desired_eth_amount, 'ether')

            print(f"{Colors.WHITE}🔄 {Colors.BOLD}Preparing liquidity addition for account:{Colors.RESET}{Colors.WHITE} {current_account.address}{Colors.RESET}")
            print(f"{Colors.WHITE}   Attempting to add {Colors.BOLD}{desired_token_amount} {SELECTED_TOKEN_NAME}{Colors.RESET}{Colors.WHITE} and {Colors.BOLD}{desired_eth_amount} NEX{Colors.RESET}...")

            if not has_sufficient_eth_balance(current_account, amount_eth_desired_wei):
                current_eth_balance = web3.from_wei(web3.eth.get_balance(current_account.address), 'ether')
                print(f"  {Colors.RED}❌ {Colors.BOLD}Insufficient NEX balance for account {current_account.address}{Colors.RESET}{Colors.RED}. Balance: {current_eth_balance} NEX. Skipping add liquidity.{Colors.RESET}")
                current_operation_retries = 0
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(1)
                continue

            current_token_balance_wei = get_token_balance(current_account.address, TOKEN_ADDRESS)
            current_token_balance = web3.from_wei(current_token_balance_wei, 'ether')
            if current_token_balance_wei < amount_token_desired_wei:
                print(f"  {Colors.RED}❌ {Colors.BOLD}Insufficient {SELECTED_TOKEN_NAME} balance for account {current_account.address}{Colors.RESET}{Colors.RED}. Balance: {current_token_balance} {SELECTED_TOKEN_NAME}. Skipping add liquidity.{Colors.RESET}")
                current_operation_retries = 0
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(1)
                continue

            if not approve_token(current_account, current_private_key, TOKEN_ADDRESS, UNISWAP_V2_ROUTER_ADDRESS, amount_token_desired_wei):
                print(f"  {Colors.RED}❌ Failed to approve token for add liquidity. Skipping add liquidity.{Colors.RESET}")
                current_operation_retries = 0
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(1)
                continue

            amount_token_min = int(amount_token_desired_wei * (1 - slippage_tolerance_percent / 100))
            amount_eth_min = int(amount_eth_desired_wei * (1 - slippage_tolerance_percent / 100))

            print(f"   {Colors.CYAN}Slippage Tolerance: {slippage_tolerance_percent}%{Colors.RESET}")
            print(f"   {Colors.CYAN}Minimum {SELECTED_TOKEN_NAME} (Add): {web3.from_wei(amount_token_min, 'ether')}{Colors.RESET}")
            print(f"   {Colors.CYAN}Minimum NEX (Add): {web3.from_wei(amount_eth_min, 'ether')}{Colors.RESET}")

            try:
                add_liquidity_eth(current_account, current_private_key, TOKEN_ADDRESS,
                                  amount_token_desired_wei, amount_eth_desired_wei,
                                  amount_token_min, amount_eth_min, deadline)
            except Exception as e:
                print(f"  {Colors.RED}❌ Add liquidity failed: {e}.{Colors.RESET}")
                current_operation_retries = 0
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(5)
                continue

            delay = random.randint(5, 15)
            print(f"\n{Colors.YELLOW}😴 Waiting {delay} seconds before next cycle...{Colors.RESET}")
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

    print(f"\n{Colors.BOLD}{Colors.MAGENTA}--- All liquidity addition operations completed. ---{Colors.RESET}")