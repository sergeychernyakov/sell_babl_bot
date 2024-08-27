# README.md

# Token Selling Bot

A bot that continuously checks for the possibility to sell a specific ERC-20 token. The bot uses the Uniswap V2 Router to swap the token for ETH. It starts by attempting to sell a large amount of tokens and decreases the amount until the entire balance is sold. The bot estimates gas requirements before executing any transaction to avoid excessive fees. If a gas amount is returned successfully, the transaction is executed with increased priority fees.

**The bot uses `.env` to store sensitive data such as the private key.**  
The token selling is performed using the `swapExactTokensForETH` method from Uniswap V2 Router.

## Bot Logic
- **Initialization:** The bot initializes by loading environment variables, setting up logging with a rotating file handler, and establishing a connection to the Ethereum network via Web3.
- **Continuous Operation:** In the main loop, the bot:
  - Checks the token balance in the wallet.
  - Estimates gas fees required for a transaction before attempting to sell tokens.
  - Executes the transaction if gas estimation is successful.
  - Logs each action and result for monitoring purposes.
- **Allowance Check:** Before executing any transaction, the bot ensures that sufficient allowance is set for the Uniswap V2 Router to spend tokens on behalf of the wallet. If not, it attempts to set an unlimited allowance.

## Project Structure
- `.env`: Contains environment variables such as the private key.
- `bot_manager.py`: Main bot code handling the logic of token selling and transaction management.

### Key Methods:
- `run()`: Main loop that manages the bot's operation.
- `sell(amount_in_wei, only_estimate=True)`: Estimates gas usage or executes a token sell transaction.
- `get_token_balance()`: Fetches the token balance in the wallet.
- `check_allowance(amount_in_wei)`: Checks if the Uniswap V2 Router has sufficient allowance to spend tokens.
- `set_allowance(amount_in_wei)`: Sets or updates the allowance for the Uniswap V2 Router.
- `build_transaction(amount_in_wei, amount_out_min_in_wei)`: Builds the transaction dictionary for selling tokens.
- `estimate_gas(transaction)`: Estimates the gas required for a transaction.
- `execute_swap(transaction)`: Executes a signed transaction on the Ethereum blockchain.

### Logging:
- The bot uses a rotating file handler to manage log files (`bot.log`) with a maximum size of 5MB per file and up to 5 backup files. This prevents the log file from growing too large.
- Log messages include transaction status, gas estimation results, allowance checks, and errors.

### Stopping the Bot Gracefully:
The bot can be stopped gracefully with a keyboard interrupt (Ctrl+C), which will log a stop message and exit the program.

```python
except (KeyboardInterrupt, SystemExit):
    logging.info("Bot received stop signal")
    bot.stop()
```

## Setup

To set up the bot locally, follow these steps:

1. Clone the repository to your local machine:
    ```sh
    git clone https://github.com/sergeychernyakov/token_selling_bot.git
    ```
2. Create a virtual environment:
    ```sh
    python3 -m venv venv
    ```
3. Activate the virtual environment:
    ```sh
    source venv/bin/activate
    ```
4. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```
5. Set environment variables:
    ```sh
    cp .env.example .env
    ```
    Edit the `.env` file to set your private key and other configurations.
6. Export the Installed Packages:
    ```sh
    pip freeze > requirements.txt
    ```
7. Run the bot:
    ```sh
    python3 bot_manager.py
    ```

### Important Notes:
- **Environment Variables:** Ensure that all required environment variables (e.g., `PK` for the private key) are set in the `.env` file.
- **Gas Fees:** Be aware of gas fees on the Ethereum network, especially during periods of high congestion.
- **Token Contract:** This bot is designed for use with ERC-20 tokens on the Ethereum blockchain. Adjust the `token_address` in the code as needed.

## Disclaimer
This bot interacts with the Ethereum blockchain and executes real transactions. Use it responsibly and ensure you understand the risks involved in automated trading. The developers are not responsible for any losses incurred.
