import requests
import json
import time
import random
from datetime import datetime, timedelta

# Load config
with open("config.json", "r") as file:
    config = json.load(file)

# Constants and configuration
API_URL = 'https://api.hyperliquid.xyz'
WS_URL = 'wss://api.hyperliquid.xyz/ws'
ACCOUNT_1_API_KEY = config["your_api_key_1"]
ACCOUNT_2_API_KEY = config["your_api_key_2"]
TRADING_PAIRS = ['ETH-USD', 'BTC-USD', 'SOL-USD']
MIN_HOLD_TIME, MAX_HOLD_TIME = config["min_hold_time"], config["max_hold_time"]  # in minutes
MIN_ORDER_FREQ, MAX_ORDER_FREQ = config["min_order_freq"], config["max_order_freq"]  # in minutes
TARGET_VOLUME = config["target_volume"]  # Target volume in USD

# Helper functions
def get_balance(account_api_key):
    # Implement function to get account balance using the Hyperliquid API
    pass

def place_market_order(account_api_key, pair, side, size):
     # URL for placing an order
    url = API_URL + "/exchange"

    # Construct the request payload
    # Note: The actual payload structure will depend on the Hyperliquid API's requirements
    payload = {
        "action": {
            "type": "order",
            "orders": [{
                "asset": pair,  # Replace with actual asset identifier if needed
                "isBuy": True if side.lower() == 'buy' else False,
                "limitPx": "market",  # Indicate that this is a market order
                "sz": size,
                "reduceOnly": False,
                "orderType": "market"  # or other appropriate key-value as per API
            }]
        },
        "nonce": int(time.time() * 1000),  # Nonce, typically current timestamp in milliseconds
        "signature": "your_signature",  # Replace with an actual signature
        # Include other necessary fields as per the API documentation
    }

    # Include headers, such as API key and content type
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {account_api_key}'  # or other appropriate header as per API
    }

    # Send the request
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response_data = response.json()

        # Check if the order was sent successfully
        if response.status_code == 200 and response_data.get('status') == 'ok':
            print("Order sent successfully.")

            # Check if the order was filled (or handle according to the API's response structure)
            if response_data.get('response', {}).get('type') == 'orderFilled':
                print("Order filled successfully.")
                return True, "Order executed successfully."
            else:
                print("Order placed but not yet filled.")
                return True, "Order placed but pending."
        else:
            error_message = response_data.get('error_message', 'Unknown error')
            print(f"Order placement failed: {error_message}")
            return False, f"Order placement failed: {error_message}"

    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return False, f"Exception occurred: {str(e)}"


def get_random_time(min_time, max_time):
    return random.randint(min_time, max_time)

def validate_order_size(size, balance):
    return size <= balance

# Main trading logic
def main():
    current_volume = 0
    while current_volume < TARGET_VOLUME:
        for pair in TRADING_PAIRS:
            # Get balances for both accounts
            balance_1 = get_balance(ACCOUNT_1_API_KEY)
            balance_2 = get_balance(ACCOUNT_2_API_KEY)

            # Determine position size (this could be user input or based on some strategy)
            position_size = config["position_size"]  

            if not validate_order_size(position_size, min(balance_1, balance_2)):
                print("Insufficient balance for the desired position size.")
                continue

            # Place hedged orders
            place_market_order(ACCOUNT_1_API_KEY, pair, 'buy', position_size)
            place_market_order(ACCOUNT_2_API_KEY, pair, 'sell', position_size)

            # Update the traded volume
            current_volume += position_size * 2

            # Hold the position for a random time between MIN_HOLD_TIME and MAX_HOLD_TIME
            hold_time = get_random_time(MIN_HOLD_TIME, MAX_HOLD_TIME) * 60  # Convert to seconds
            time.sleep(hold_time)

            # Close the positions
            place_market_order(ACCOUNT_1_API_KEY, pair, 'sell', position_size)
            place_market_order(ACCOUNT_2_API_KEY, pair, 'buy', position_size)

            # Wait for a random time before the next order
            order_freq = get_random_time(MIN_ORDER_FREQ, MAX_ORDER_FREQ) * 60  # Convert to seconds
            time.sleep(order_freq)

if __name__ == "__main__":
    main()
