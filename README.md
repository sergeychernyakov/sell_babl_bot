# README.md

# Token Selling Bot

A bot that continuously checks for the possibility to sell a token. Once trading becomes open, it sells the tokens. It tries various token amount ranges - starting from a large amount and decreasing down to 1. It first estimates the gas required for a transaction, and if a gas amount is returned, it proceeds with the transaction with increased fees. If the transaction succeeds, it continues until the entire token balance is sold.

**Uses `.env` to store private data.**  
Uses `swapExactTokensForETH` to sell tokens.

## Configuration
- `WEBSOCKET_URI`: WebSocket endpoint for the Ethereum node
- `TOKEN_ADDRESS`: Address of the token to sell
- `WETH_ADDRESS`: Address of WETH (used for swapping)

## Bot Logic
The bot continuously attempts to sell tokens via `swapExactTokensForETH` on Uniswap. It fetches the total token balance in the wallet and attempts to sell everything, lowering the amount by half each time until the amount reaches 1 token. To avoid excessive fees, it estimates the gas required before each transaction. If a gas amount is returned, the transaction is executed with an increased fee. Successful transactions are logged, and the bot continues until the entire token balance is sold. All events such as wallet balance, sell attempts, etc., are logged in a file.

## Project Structure
- `.env`: Environment variables
- `bot_manager.py`: Main bot code

### Methods:
- `run`: Main loop to run the bot.
- `sell(only_estimate)`: Method to estimate gas or execute a sell.

### Stopping the Bot Gracefully:
```python
except (KeyboardInterrupt, SystemExit):
    logging.info("Bot received stop signal")
```

## Setup

To set up the app locally, follow these steps:

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
    Then edit `.env` to set your configurations.
6. Export the Installed Packages:
    ```sh
    pip freeze > requirements.txt
    ```
7. Run the app:
    ```sh
    python3 bot_manager.py
    ```

### Note:
This bot is designed for use with ERC-20 tokens on the Ethereum blockchain. Ensure that all environmental variables are properly configured in the `.env` file.


Plan:
  show logs also in the console
  use Web3.to_checksum_address

ERROR:root:Error occurred: ('web3.py only accepts checksum addresses. The software that gave you this non-checksum address should be considered unsafe, please file it as a bug on their platform. Try using an ENS name instead. Or, if you must accept lower safety, use Web3.to_checksum_address(lower_case_address).', '0x0984020d31e52ded8283fdd798e8f544c085a999')
ERROR:root:Error occurred: ('web3.py only accepts checksum addresses. The software that gave you this non-checksum address should be considered unsafe, please file it as a bug on their platform. Try using an ENS name instead. Or, if you must accept lower safety, use Web3.to_checksum_address(lower_case_address).', '0x0984020d31e52ded8283fdd798e8f544c085a999')


