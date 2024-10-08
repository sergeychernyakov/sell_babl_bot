# bot_manager.py

import os
import logging
import time
from web3 import Web3
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

class BotManager:
    MAX_PRIORITY_FEE_PER_GAS = Web3.to_wei(2, 'gwei')  # Constant priority fee for transactions
    GAS_LIMIT = 400000

    def __init__(self):
        """
        Initializes the BotManager class by setting up Web3, loading environment variables, and configuring logging.
        """
        load_dotenv()  # Load environment configurations from .env file

        # Set up logging to both console and file
        self.setup_logging()

        # Load private key from environment variables
        self.private_key = os.getenv('PK')

        # Configuration parameters loaded from environment or default values
        self.token_address = Web3.to_checksum_address('0x0984020D31E52ded8283FDD798E8f544c085A999') # Default token BABL
        self.weth_address = Web3.to_checksum_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')  # WETH address for swaps
        self.router_address = Web3.to_checksum_address('0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D')  # Uniswap V2 Router address

        # Initialize Web3 with the provided WebSocket URI
        self.web3 = Web3(Web3.LegacyWebSocketProvider('ws://192.168.3.118:8546'))

        # Get the wallet account from the private key
        self.account = self.web3.eth.account.from_key(self.private_key)
        self.wallet_address = self.account.address  # Store the wallet address

        logging.info(f"Bot initialized on wallet: https://etherscan.io/address/{self.wallet_address}")

    def setup_logging(self):
        """
        Sets up logging to both file and console.
        """
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        # File handler
        file_handler = RotatingFileHandler('tmp/bot.log', maxBytes=5*1024*1024, backupCount=5)
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    def run(self):
        """
        Main loop of the bot. Continuously checks the token balance and tries to sell the tokens.
        """
        logging.info(f"Bot started on wallet: https://etherscan.io/address/{self.wallet_address}")
        
        token_balance = self.get_token_balance()
        
        # Check and set allowance if not sufficient
        if not self.check_allowance(token_balance):
            logging.info("Allowance is insufficient.")
            return

        while True:
            try:
                # Get the current token balance of the wallet
                token_balance = self.get_token_balance()
                logging.info(f'Current token balance: {round(self.web3.from_wei(token_balance, "ether"))} tokens')

                # Attempt to sell tokens starting with the full balance, halving the amount each iteration
                amount_in_wei = token_balance
                while amount_in_wei >= 1000000000000000000:
                    # Estimate gas for the transaction
                    estimated_gas = self.sell(amount_in_wei, only_estimate=True)

                    # If gas estimation is successful, proceed with the actual transaction
                    if estimated_gas:
                        result = self.sell(amount_in_wei, only_estimate=False)
                        if result is None:  # Exit the loop if the transaction failed
                            logging.info("Exiting loop due to failed transaction.")
                            return
                    else:
                        logging.info(f'Skipping transaction for <<<   {round(self.web3.from_wei(amount_in_wei, "ether"))}   >>> tokens due to gas estimation failure.')

                    # Halve the amount for the next transaction
                    amount_in_wei //= 2

                    time.sleep(0.1)

                # Exit loop if balance is 0 to prevent unnecessary operations
                if token_balance == 0:
                    logging.info("Token balance is 0. Exiting loop.")
                    break

            except Exception as e:
                logging.error(f"Unexpected error occurred: {str(e)}")  # Use for general unexpected errors

    def get_token_balance(self) -> int:
        """
        Fetches the balance of the specified ERC-20 token in the wallet.
        
        Returns:
        - int: The balance of the token in Wei.
        """
        # Interact with the ERC-20 contract using its ABI and address
        contract = self.web3.eth.contract(address=self.token_address, abi=self.get_erc20_abi())
        # Call the balanceOf function to get the balance of the wallet
        balance = contract.functions.balanceOf(self.wallet_address).call()
        return balance

    def check_allowance(self, amount_in_wei: int) -> bool:
        """
        Checks if the allowance set for the router is sufficient.

        Parameters:
        - amount_in_wei (int): The amount of tokens intended to sell, in Wei.

        Returns:
        - bool: True if the current allowance is sufficient, False otherwise.
        """
        try:
            contract = self.web3.eth.contract(address=self.token_address, abi=self.get_erc20_abi())
            current_allowance = contract.functions.allowance(self.wallet_address, self.router_address).call()
            return current_allowance >= amount_in_wei
        except Exception as e:
            logging.error(f"Failed to check allowance: {str(e)}")
            return False

    def set_allowance(self, amount_in_wei: int) -> bool:
        """
        Sets the allowance for the Uniswap V2 Router to spend tokens.

        Parameters:
        - amount_in_wei (int): The amount of tokens to allow the router to spend, in Wei.

        Returns:
        - bool: True if the transaction was successful, otherwise False.
        """
        try:
            contract = self.web3.eth.contract(address=self.token_address, abi=self.get_erc20_abi())
            txn = contract.functions.approve(self.router_address, amount_in_wei).build_transaction({
                'from': self.wallet_address,
                'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
                'gas': 50000,
                'maxPriorityFeePerGas': self.MAX_PRIORITY_FEE_PER_GAS,
                'maxFeePerGas': self.get_current_gas_price(),
            })
            signed_txn = self.account.sign_transaction(txn)
            tx_hash = self.web3.eth.send_raw_transaction(signed_txn.raw_transaction)
            logging.info(f"Approval transaction sent: https://etherscan.io/tx/0x{tx_hash.hex()}")
            self.web3.eth.wait_for_transaction_receipt(tx_hash)
            return True
        except Exception as e:
            logging.error(f"Setting allowance failed: {str(e)}")
            return False

    def sell(self, amount_in_wei: int, amount_out_min_in_wei: int = 0, only_estimate: bool = True) -> int | None:
        """
        Sells a specified amount of the token, either by estimating gas usage or executing the transaction.

        Parameters:
        - amount_in_wei (int): The amount of tokens to sell, in Wei.
        - amount_out_min_in_wei (int): The minimum amount of output token to receive, in Wei.
        - only_estimate (bool): If True, only estimates gas usage without executing the transaction.

        Returns:
        - int: Estimated gas amount if only_estimate is True, otherwise None.
        """
        # Build the transaction dictionary
        transaction = self.build_transaction(amount_in_wei, amount_out_min_in_wei)

        if only_estimate:
            # Estimate the gas required for the transaction
            return self.estimate_gas(transaction)

        try:
            # Execute the swap transaction and log the transaction hash
            tx_hash = self.execute_swap(transaction)
            logging.info(f"Transaction sent: https://etherscan.io/tx/{tx_hash}")
            # Wait for transaction receipt to confirm success
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt['status'] == 1:
                logging.info(f'Transaction successful for {round(self.web3.from_wei(amount_in_wei, "ether"))} tokens')
            else:
                logging.error(f'Transaction failed for {round(self.web3.from_wei(amount_in_wei, "ether"))} tokens. Exiting loop.')
                return None  # Exit the loop if the transaction failed
        except Exception as e:
            # Log errors if transaction fails
            logging.error(f'Transaction failed for {round(self.web3.from_wei(amount_in_wei, "ether"))} tokens: {str(e)}')

        return None

    def build_transaction(self, amount_in_wei: int, amount_out_min_in_wei: int) -> dict:
        """
        Builds a transaction for swapping tokens using Uniswap V2 Router.

        Parameters:
        - amount_in_wei (int): The amount of tokens to sell, in Wei.
        - amount_out_min_in_wei (int): The minimum amount of output token to receive, in Wei.

        Returns:
        - dict: The transaction dictionary containing necessary details for execution.
        """
        # Interact with the Uniswap V2 Router contract using its ABI
        router_contract = self.web3.eth.contract(address=self.router_address, abi=self.get_uniswap_v2_router_abi())

        # Build the transaction using the Uniswap V2 `swapExactTokensForETH` method
        transaction = router_contract.functions.swapExactTokensForETH(
            amount_in_wei, amount_out_min_in_wei, [self.token_address, self.weth_address], self.wallet_address, int(time.time()) + 60
        ).build_transaction({
            'from': self.wallet_address,
            'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
            'gas': self.GAS_LIMIT,
            'maxPriorityFeePerGas': self.MAX_PRIORITY_FEE_PER_GAS,  # Set priority fee for transaction speed
            'maxFeePerGas': self.get_current_gas_price()  # Set maximum fee for the transaction based on real-time gas price
        })
        return transaction

    def get_current_gas_price(self) -> int:
        """
        Fetches the base fee from the latest block and calculates the maximum fee per gas
        by adding the constant MAX_PRIORITY_FEE_PER_GAS.

        Returns:
        - int: The maximum fee per gas in Wei, which includes the base fee and max priority fee.
        """
        latest_block = self.web3.eth.get_block('latest')  # Get the latest block
        base_fee = latest_block['baseFeePerGas']  # Fetch the base fee per gas from the latest block
        max_priority_fee = self.MAX_PRIORITY_FEE_PER_GAS  # Use the constant priority fee
        max_fee_per_gas = base_fee + max_priority_fee  # Calculate the total max fee per gas
        return max_fee_per_gas

    def estimate_gas(self, transaction: dict) -> int | None:
        """
        Estimates the gas required for a given transaction.
        
        Parameters:
        - transaction (dict): The transaction dictionary to estimate gas for.
        
        Returns:
        - int: The estimated gas amount, or None if estimation fails.
        """
        try:
            # Estimate gas usage for the transaction
            estimated_gas = self.web3.eth.estimate_gas(transaction)
            return estimated_gas
        except Exception as e:
            # Log errors if gas estimation fails
            logging.error(f"Gas estimation failed: {str(e)[:58]}")
            return None

    def execute_swap(self, transaction: dict) -> str:
        """
        Executes a token swap transaction by signing and sending it.
        
        Parameters:
        - transaction (dict): The transaction dictionary to execute.
        
        Returns:
        - str: The transaction hash as a string if successful.
        """
        # Sign the transaction with the private key
        signed_tx = self.account.sign_transaction(transaction)
        # Send the signed transaction to the blockchain network
        # return '0xc76d55f2a75a8f5a935f26082f0029dfad96c3bb18752b1b0da303a92ef0611c' # testing result
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return tx_hash.hex()

    def get_erc20_abi(self) -> list:
        """
        Provides the standard ABI for ERC-20 tokens.

        Returns:
        - list: A list representing the ABI for standard ERC-20 functions.
        """
        # ABI definition for the ERC-20 token interface
        return [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": False,
                "inputs": [
                    {"name": "_spender", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "approve",
                "outputs": [{"name": "success", "type": "bool"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [
                    {"name": "_owner", "type": "address"},
                    {"name": "_spender", "type": "address"}
                ],
                "name": "allowance",
                "outputs": [{"name": "remaining", "type": "uint256"}],
                "type": "function"
            }
        ]

    def get_uniswap_v2_router_abi(self) -> list:
        """
        Provides the ABI for the Uniswap V2 Router.

        Returns:
        - list: A list representing the ABI for Uniswap V2 Router functions.
        """
        # Full ABI for Uniswap V2 Router to handle various functions
        return [
            {
                "inputs": [{"internalType": "address", "name": "_factory", "type": "address"}, {"internalType": "address", "name": "_WETH", "type": "address"}],
                "stateMutability": "nonpayable",
                "type": "constructor"
            },
            {
                "inputs": [],
                "name": "WETH",
                "outputs": [{"internalType": "address", "name": "", "type": "address"}],
                "stateMutability": "view",
                "type": "function"
            },
            # ... (Other Uniswap V2 functions)
            {
                "constant": False,
                "inputs": [
                    {"name": "amountIn", "type": "uint256"},
                    {"name": "amountOutMin", "type": "uint256"},
                    {"name": "path", "type": "address[]"},
                    {"name": "to", "type": "address"},
                    {"name": "deadline", "type": "uint256"}
                ],
                "name": "swapExactTokensForETH",
                "outputs": [{"name": "amounts", "type": "uint256[]"}],
                "type": "function"
            }
        ]

    def stop(self):
        """
        Stops the bot gracefully by logging a stop message and exiting.
        """
        logging.info("Bot received stop signal")
        exit(0)

# Example usage section to demonstrate how to run the script
# python3 bot_manager.py
if __name__ == '__main__':
    bot = BotManager()  # Create an instance of the BotManager class
    try:
        bot.run()  # Start the bot's main loop
    except (KeyboardInterrupt, SystemExit):
        bot.stop()  # Stop the bot if a keyboard interrupt or system exit signal is received
