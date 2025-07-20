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

LP_TOKEN_ADDRESSES = {
    "NXS": "0x053d715880A9A269199186B8BF26909cc6725763",
    "NEXI": "0xFA1BB4324F96Ba4264B95Af1ae706E77ED5B90A8",
    "AIE": "0xa47b8266D2e5a23275a4679254eF46d883576Bf4"
}

TOKEN_ADDRESS = ""
SELECTED_TOKEN_NAME = ""
LP_TOKEN_ADDRESS = ""

web3 = Web3(Web3.HTTPProvider(RPC_URL))
if not web3.is_connected():
    raise ConnectionError(f"{Colors.RED}Failed to connect to RPC URL{Colors.RESET}")

uniswap_v2_router_abi = '''
[
    {
        "inputs": [
            {"internalType": "address", "name": "token", "type": "address"},
            {"internalType": "uint256", "name": "liquidity", "type": "uint256"},
            {"internalType": "uint256", "name": "amountTokenMin", "type": "uint256"},
            {"internalType": "uint256", "name": "amountETHMin", "type": "uint256"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "removeLiquidityETH",
        "outputs": [
            {"internalType": "uint256", "name": "amountToken", "type": "uint256"},
            {"internalType": "uint256", "name": "amountETH", "type": "uint256"}
        ],
        "stateMutability": "nonpayable",
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
    },
    {
        "constant": true,
        "inputs": [],
        "name": "totalSupply",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "type": "function"
    }
]
'''

uniswap_v2_pair_abi = '''
[
    {
        "constant": true,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"internalType": "uint112", "name": "_reserve0", "type": "uint256"},
            {"internalType": "uint112", "name": "_reserve1", "type": "uint256"},
            {"internalType": "uint32", "name": "blockTimestampLast", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "token0",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": true,
        "inputs": [],
        "name": "token1",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]
'''

uniswap_router = web3.eth.contract(address=Web3.to_checksum_address(UNISWAP_V2_ROUTER_ADDRESS), abi=uniswap_v2_router_abi)

def get_erc20_contract(address):
    return web3.eth.contract(address=web3.to_checksum_address(address), abi=erc20_abi)

def get_pair_contract(pair_address):
    return web3.eth.contract(address=web3.to_checksum_address(pair_address), abi=uniswap_v2_pair_abi)

def get_token_balance(account_address, token_address):
    token_contract = get_erc20_contract(token_address)
    return token_contract.functions.balanceOf(account_address).call()

def approve_token(account, private_key, token_address, router_address, amount_to_approve):
    token_contract = get_erc20_contract(token_address)
    gas_price = web3.eth.gas_price

    while True:
        try:
            nonce = web3.eth.get_transaction_count(account.address, "pending")
            print(f"  {Colors.YELLOW}⏳ Approving {web3.from_wei(amount_to_approve, 'ether')} LP Token for Nexswap router...{Colors.RESET}")

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
            print(f"  {Colors.GREEN}✅ {Colors.BOLD}Approval transaction sent{Colors.RESET}{Colors.GREEN}: https://testnet3.explorer.nexus.xyz/tx/{web3.to_hex(tx_hash)}{Colors.RESET}")
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

def remove_liquidity_eth(account, private_key, token_address, liquidity_amount, amount_token_min, amount_eth_min, deadline):
    gas_price = web3.eth.gas_price

    while True:
        try:
            nonce = web3.eth.get_transaction_count(account.address, "pending")
            print(f"  {Colors.YELLOW}⏳ Removing liquidity for {SELECTED_TOKEN_NAME}/NEX...{Colors.RESET}")

            transaction = uniswap_router.functions.removeLiquidityETH(
                web3.to_checksum_address(token_address),
                liquidity_amount,
                amount_token_min,
                amount_eth_min,
                account.address,
                deadline
            ).build_transaction({
                'from': account.address,
                'value': 0,
                'gas': 320000,
                'gasPrice': gas_price,
                'nonce': nonce,
                'chainId': CHAIN_ID
            })

            signed_txn = web3.eth.account.sign_transaction(transaction, private_key=private_key)
            tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            print(f"  {Colors.GREEN}✅ {Colors.BOLD}Remove liquidity transaction sent{Colors.RESET}{Colors.GREEN} https://testnet3.explorer.nexus.xyz/tx/{web3.to_hex(tx_hash)}{Colors.RESET}")
            web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
            print(f"{Colors.GREEN}  🎉 Liquidity removal for {SELECTED_TOKEN_NAME}/NEX confirmed!{Colors.RESET}")
            return web3.to_hex(tx_hash)

        except Exception as e:
            if 'replacement transaction underpriced' in str(e) or 'nonce too low' in str(e):
                gas_price += web3.to_wei(2, 'gwei')
                print(f"  {Colors.YELLOW}⚠️ Gas price too low or nonce issue for remove liquidity, increasing to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            elif 'out of gas' in str(e):
                gas_price += web3.to_wei(5, 'gwei')
                print(f"  {Colors.RED}🔥 Remove liquidity transaction ran out of gas, increasing gas price to {web3.from_wei(gas_price, 'gwei')} gwei and retrying...{Colors.RESET}")
            else:
                print(f"  {Colors.RED}❌ An error occurred during remove liquidity: {e}{Colors.RESET}")
                raise

if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.MAGENTA}--- 💸 Nexswap Liquidity Remover 💸 ---{Colors.RESET}")

    print(f"\n{Colors.BOLD}{Colors.BLUE}--- Select Liquidity Pair Token (with NEX) ---{Colors.RESET}")
    token_names = list(AVAILABLE_TOKENS.keys())
    for i, token_name in enumerate(token_names):
        print(f"{Colors.WHITE}{i+1}. {token_name} ({AVAILABLE_TOKENS[token_name]}){Colors.RESET}")

    while True:
        try:
            choice = int(input(f"{Colors.CYAN}Enter the number of the token for the liquidity pair you want to remove: {Colors.RESET}"))
            if 1 <= choice <= len(token_names):
                SELECTED_TOKEN_NAME = token_names[choice - 1]
                TOKEN_ADDRESS = AVAILABLE_TOKENS[SELECTED_TOKEN_NAME]
                print(f"{Colors.GREEN}✅ You selected: {Colors.BOLD}{SELECTED_TOKEN_NAME}{Colors.RESET}{Colors.GREEN}/NEX{Colors.RESET}")
                break
            else:
                print(f"{Colors.RED}Invalid choice. Please enter a valid number.{Colors.RESET}")
        except ValueError:
            print(f"{Colors.RED}Invalid input. Please enter a number.{Colors.RESET}")

    LP_TOKEN_ADDRESS = LP_TOKEN_ADDRESSES.get(SELECTED_TOKEN_NAME)
    if not LP_TOKEN_ADDRESS:
        print(f"{Colors.RED}❌ LP token address for {SELECTED_TOKEN_NAME} not found in the provided list. Please ensure it's added.{Colors.RESET}")
        exit()
    print(f"{Colors.CYAN}ℹ️ Associated LP Token Address: {LP_TOKEN_ADDRESS}{Colors.RESET}")

    remove_amount_lp = 0.0
    remove_percentage = 0.0
    remove_by_percentage = False

    while True:
        mode_choice = input(f"{Colors.CYAN}\nDo you want to remove liquidity by:\n1. LP Token Amount\n2. Percentage of your total LP Tokens\nChoose mode (1 or 2): {Colors.RESET}").strip()
        if mode_choice == '1':
            try:
                remove_amount_lp = float(input(f"{Colors.CYAN}Enter the amount of LP Tokens you want to remove (e.g., 0.01): {Colors.RESET}"))
                if remove_amount_lp <= 0:
                    raise ValueError("LP Token amount must be positive.")
                break
            except ValueError as e:
                print(f"{Colors.RED}Invalid input: {e}. Please enter a number.{Colors.RESET}")
        elif mode_choice == '2':
            try:
                remove_percentage = float(input(f"{Colors.CYAN}Enter the percentage of LP Tokens you want to remove (e.g., 50 for 50%): {Colors.RESET}"))
                if not (0 < remove_percentage <= 100):
                    raise ValueError("Percentage must be between 0 (exclusive) and 100 (inclusive).")
                remove_by_percentage = True
                break
            except ValueError as e:
                print(f"{Colors.RED}Invalid input: {e}. Please enter a number.{Colors.RESET}")
        else:
            print(f"{Colors.RED}Invalid choice. Please enter '1' or '2'.{Colors.RESET}")

    run_in_loop = False
    while True:
        loop_choice = input(f"{Colors.CYAN}\nDo you want to run liquidity removal in a continuous loop? (yes/no): {Colors.RESET}").lower().strip()
        if loop_choice in ['yes', 'y']:
            run_in_loop = True
            print(f"{Colors.GREEN}✅ Loop mode activated. Liquidity removal will run continuously.{Colors.RESET}")
            break
        elif loop_choice in ['no', 'n']:
            run_in_loop = False
            print(f"{Colors.GREEN}✅ Single execution mode. Liquidity removal will run once for each account.{Colors.RESET}")
            break
        else:
            print(f"{Colors.RED}Invalid choice. Please enter 'yes' or 'no'.{Colors.RESET}")

    slippage_tolerance_percent = 0.5

    deadline = int(web3.eth.get_block('latest').timestamp) + 300

    accounts = [web3.eth.account.from_key(pk) for pk in PRIVATE_KEYS]
    account_index = 0

    print(f"\n{Colors.BOLD}{Colors.MAGENTA}--- Starting Liquidity Removal Operations ---{Colors.RESET}")

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

            current_lp_balance_wei = get_token_balance(current_account.address, LP_TOKEN_ADDRESS)
            current_lp_balance = web3.from_wei(current_lp_balance_wei, 'ether')
            print(f"   {Colors.CYAN}Your LP Token ({SELECTED_TOKEN_NAME}/NEX) Balance: {current_lp_balance:.8f}{Colors.RESET}")

            liquidity_to_remove_wei = 0
            if remove_by_percentage:
                liquidity_to_remove_wei = int(current_lp_balance_wei * (remove_percentage / 100.0))
                if liquidity_to_remove_wei == 0 and current_lp_balance_wei > 0:
                    liquidity_to_remove_wei = 1
                print(f"   {Colors.WHITE}Removing {Colors.BOLD}{remove_percentage:.2f}%{Colors.RESET}{Colors.WHITE} of your LP Tokens: {web3.from_wei(liquidity_to_remove_wei, 'ether')} LP Tokens{Colors.RESET}")
            else:
                liquidity_to_remove_wei = web3.to_wei(remove_amount_lp, 'ether')
                print(f"   {Colors.WHITE}Removing specified LP Token amount: {remove_amount_lp} LP Tokens{Colors.RESET}")


            if current_lp_balance_wei == 0:
                print(f"  {Colors.RED}❌ Account {current_account.address} has no LP Tokens. Skipping liquidity removal.{Colors.RESET}")
                current_operation_retries = 0
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(1)
                continue

            if liquidity_to_remove_wei == 0:
                print(f"  {Colors.CYAN}ℹ️ Amount of LP Tokens to remove is zero. Skipping liquidity removal.{Colors.RESET}")
                current_operation_retries = 0
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(1)
                continue

            if current_lp_balance_wei < liquidity_to_remove_wei:
                print(f"  {Colors.RED}❌ Insufficient LP Token balance for account {current_account.address}. You want to remove {web3.from_wei(liquidity_to_remove_wei, 'ether')}, but only have {current_lp_balance} LP Tokens. Skipping liquidity removal.{Colors.RESET}")
                current_operation_retries = 0
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(1)
                continue

            if not approve_token(current_account, current_private_key, LP_TOKEN_ADDRESS, UNISWAP_V2_ROUTER_ADDRESS, liquidity_to_remove_wei):
                print(f"  {Colors.RED}❌ Failed to approve LP Token for remove liquidity. Skipping remove liquidity.{Colors.RESET}")
                current_operation_retries = 0
                account_index = (account_index + 1) % len(accounts)
                if not run_in_loop and account_index == 0:
                    break
                time.sleep(1)
                continue

            pair_contract = get_pair_contract(LP_TOKEN_ADDRESS)
            reserves = pair_contract.functions.getReserves().call()
            total_lp_supply = get_erc20_contract(LP_TOKEN_ADDRESS).functions.totalSupply().call()

            token0_address = pair_contract.functions.token0().call()
            token1_address = pair_contract.functions.token1().call()

            reserve_token_address = web3.to_checksum_address(TOKEN_ADDRESS)
            weth_token_address = web3.to_checksum_address(WETH_ADDRESS)

            reserve_token = 0
            reserve_eth = 0

            if token0_address == reserve_token_address and token1_address == weth_token_address:
                reserve_token = reserves[0]
                reserve_eth = reserves[1]
            elif token0_address == weth_token_address and token1_address == reserve_token_address:
                reserve_token = reserves[1]
                reserve_eth = reserves[0]
            else:
                print(f"  {Colors.RED}❌ Warning: Token order in pool is not as expected. There might be an issue with token or WETH addresses.{Colors.RESET}")
                reserve_token = reserves[0]
                reserve_eth = reserves[1]

            expected_token_out_wei = int(reserve_token * liquidity_to_remove_wei / total_lp_supply)
            expected_eth_out_wei = int(reserve_eth * liquidity_to_remove_wei / total_lp_supply)

            amount_token_min = int(expected_token_out_wei * (1 - slippage_tolerance_percent / 100))
            amount_eth_min = int(expected_eth_out_wei * (1 - slippage_tolerance_percent / 100))

            print(f"   {Colors.CYAN}Slippage Tolerance: {slippage_tolerance_percent}%{Colors.RESET}")
            print(f"   {Colors.CYAN}Estimated {SELECTED_TOKEN_NAME} to receive: {web3.from_wei(expected_token_out_wei, 'ether')} (Min: {web3.from_wei(amount_token_min, 'ether')}){Colors.RESET}")
            print(f"   {Colors.CYAN}Estimated NEX to receive: {web3.from_wei(expected_eth_out_wei, 'ether')} (Min: {web3.from_wei(amount_eth_min, 'ether')}){Colors.RESET}")

            try:
                remove_liquidity_eth(current_account, current_private_key, TOKEN_ADDRESS,
                                     liquidity_to_remove_wei, amount_token_min, amount_eth_min, deadline)
            except Exception as e:
                print(f"  {Colors.RED}❌ Remove liquidity failed: {e}.{Colors.RESET}")
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

    print(f"\n{Colors.BOLD}{Colors.MAGENTA}--- All liquidity removal operations completed. ---{Colors.RESET}")