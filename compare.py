# src/bot_manager.py

import os
import logging
import time
from web3 import Web3
from web3.providers.websocket import LegacyWebSocketProvider
from dotenv import load_dotenv

class BotManager:
    MAX_PRIORITY_FEE_PER_GAS = Web3.to_wei(2, 'gwei')  # Constant priority fee for transactions

    def __init__(self):
        """
        Initializes the BotManager class by setting up Web3, loading environment variables, and configuring logging.
        """
        load_dotenv()  # Load environment configurations from .env file

        # Load private key from environment variables
        self.private_key = os.getenv('PK')

        # Configuration parameters loaded from environment or default values
        self.token_address = '0x0984020d31e52ded8283fdd798e8f544c085a999' # Default token
        self.weth_address = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'  # WETH address for swaps

        # Initialize Web3 with the provided WebSocket URI using LegacyWebSocketProvider
        self.web3 = Web3(LegacyWebSocketProvider('ws://192.168.3.118:8546'))

        # Get the wallet account from the private key
        self.account = self.web3.eth.account.privateKeyToAccount(self.private_key)
        self.wallet_address = self.account.address  # Store the wallet address

        # Set up logging to a file named 'bot.log'
        logging.basicConfig(filename='bot.log', level=logging.INFO)
        logging.info('Bot initialized')

    def run(self):
        """
        Main loop of the bot. Continuously checks the token balance and tries to sell the tokens.
        """
        logging.info("Bot started")
        while True:
            try:
                # Get the current token balance of the wallet
                token_balance = self.get_token_balance()
                logging.info(f'Current token balance: {token_balance} tokens')

                # Attempt to sell tokens starting with the full balance, halving the amount each iteration
                amount = token_balance
                while amount >= 1:
                    # Estimate gas for the transaction
                    estimated_gas = self.sell(amount, only_estimate=True)

                    # If gas estimation is successful, proceed with the actual transaction
                    if estimated_gas:
                        self.sell(amount, only_estimate=False)
                    else:
                        logging.info(f"Skipping transaction for {amount} tokens due to gas estimation failure")
                    
                    # Halve the amount for the next transaction
                    amount /= 2

                # Exit loop if balance is 0 to prevent unnecessary operations
                if token_balance == 0:
                    logging.info("Token balance is 0. Exiting loop.")
                    break

            except Exception as e:
                # Log any unexpected errors
                logging.error(f"Error occurred: {str(e)}")

    def get_token_balance(self) -> float:
        """
        Fetches the balance of the specified ERC-20 token in the wallet.
        
        Returns:
        - float: The balance of the token in Ether units.
        """
        # Interact with the ERC-20 contract using its ABI and address
        contract = self.web3.eth.contract(address=self.token_address, abi=self.get_abi())
        # Call the balanceOf function to get the balance of the wallet
        balance = contract.functions.balanceOf(self.wallet_address).call()
        # Convert the balance from Wei to Ether for easier reading
        return self.web3.from_wei(balance, 'ether')

    def sell(self, amount: float, only_estimate: bool = True) -> int | None:
        """
        Sells a specified amount of the token, either by estimating gas usage or executing the transaction.
        
        Parameters:
        - amount (float): The amount of tokens to sell.
        - only_estimate (bool): If True, only estimates gas usage without executing the transaction.
        
        Returns:
        - int: Estimated gas amount if only_estimate is True, otherwise None.
        """
        # Build the transaction dictionary
        transaction = self.build_transaction(amount)

        if only_estimate:
            # Estimate the gas required for the transaction
            return self.estimate_gas(transaction)

        try:
            # Execute the swap transaction and log the transaction hash
            tx_hash = self.execute_swap(transaction)
            logging.info(f"Transaction sent: {tx_hash}")
            # Wait for transaction receipt to confirm success
            self.web3.eth.wait_for_transaction_receipt(tx_hash)
            logging.info(f"Transaction successful for {amount} tokens")
        except Exception as e:
            # Log errors if transaction fails
            logging.error(f"Transaction failed for {amount} tokens: {str(e)}")
        return None

    def build_transaction(self, amount: float) -> dict:
        """
        Builds a transaction for swapping tokens for ETH.
        
        Parameters:
        - amount (float): The amount of tokens to sell.
        
        Returns:
        - dict: The transaction dictionary containing necessary details for execution.
        """
        # Interact with the token contract using its ABI
        contract = self.web3.eth.contract(address=self.token_address, abi=self.get_abi())

        # Build the transaction to swap tokens for ETH
        transaction = contract.functions.swapExactTokensForETH(
            amount, 0, [self.token_address, self.weth_address], self.wallet_address, int(time.time()) + 60
        ).buildTransaction({
            'from': self.wallet_address,
            'nonce': self.web3.eth.get_transaction_count(self.wallet_address),
            'maxPriorityFeePerGas': self.MAX_PRIORITY_FEE_PER_GAS,  # Set priority fee for transaction speed
            'maxFeePerGas': self.get_current_gas_price()  # Set maximum fee for the transaction based on real-time gas price
        })
        return transaction

    def get_current_gas_price(self) -> int:
        """
        Fetches the current gas price from the network.
        
        Returns:
        - int: Current gas price in Wei.
        """
        return self.web3.eth.gas_price

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
            logging.error(f"Gas estimation failed: {str(e)}")
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
        signed_tx = self.web3.eth.account.sign_transaction(transaction, private_key=self.private_key)
        # Send the signed transaction to the blockchain network
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        return tx_hash.hex()

    def get_abi(self) -> list:
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
