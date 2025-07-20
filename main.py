import os
from colorama import Fore, Style, init

init(autoreset=True)

from banner import banner

print(banner)

def main():
    while True:
        print(Fore.CYAN + "\nSelect Option:")
        print(Fore.CYAN + "1. Swap")
        print(Fore.CYAN + "2. Unswap")
        print(Fore.CYAN + "3. Swap & Unswap")
        print(Fore.CYAN + "4. Add Liquidity")
        print(Fore.CYAN + "5. Remove Liquidity")
        print(Fore.CYAN + "6. All Feature")
        print(Fore.CYAN + "0. Exit\n")

        pilihan = input(Fore.CYAN + "Select Option (1-6): " + Style.RESET_ALL)
        
        if pilihan == "1":
            os.system('cls' if os.name == 'nt' else 'clear')
            os.system("python feature/swap.py")
        elif pilihan == "2":
            os.system('cls' if os.name == 'nt' else 'clear')
            os.system("python feature/unswap.py")
        elif pilihan == "3":
            os.system('cls' if os.name == 'nt' else 'clear')
            os.system("python feature/swapunswap.py")
        elif pilihan == "4":
            os.system('cls' if os.name == 'nt' else 'clear')
            os.system("python feature/addliquidity.py")
        elif pilihan == "5":
            os.system('cls' if os.name == 'nt' else 'clear')
            os.system("python feature/removeliquidity.py")
        elif pilihan == "6":
            os.system('cls' if os.name == 'nt' else 'clear')
            os.system("python feature/allfeature.py")
        elif pilihan == "0":
            print(Fore.RED + "Exit the program." + Style.RESET_ALL)
            break
        else:
            print(Fore.RED + "[INFO] Invalid selection, please select 1-6" + Style.RESET_ALL)

if __name__ == "__main__":
    main()
