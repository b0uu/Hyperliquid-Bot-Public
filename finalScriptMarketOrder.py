import requests
import threading
import json
import time
import math
import random
from datetime import datetime, timedelta
import eth_account
import utils
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from hyperliquid.utils import types


# Load config
with open("config.json", "r") as file:
    config = json.load(file)

account_1 = eth_account.Account.from_key(config["account_1_api_key"])
account_2 = eth_account.Account.from_key(config["account_2_api_key"])

api_1 = config["account_1_api_key"]
api_2 = config["account_2_api_key"]



TRADING_COIN = config["coin"]
MIN_HOLD_TIME, MAX_HOLD_TIME = config["min_hold_time"], config["max_hold_time"]  # in seconds
MIN_ORDER_FREQ, MAX_ORDER_FREQ = config["min_order_freq"], config["max_order_freq"]  # in seconds
TARGET_VOLUME = config["target_volume"]  # Target volume in USD


def get_specific_mid_prices(assets):
    # API endpoint
    url = 'https://api.hyperliquid.xyz/info'

    # Request payload
    payload = {"type": "allMids"}

    # Headers
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        # Make the POST request
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad requests

        # Parsing the response to JSON
        mid_prices = response.json()

        # Filter and return only the specified assets' mid prices
        return {asset: mid_prices[asset] for asset in assets if asset in mid_prices}

    except requests.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    
# Specify the assets for which you want the mid prices
desired_assets = ['BTC', 'ETH', 'SOL']

# Fetch mid prices for specific assets
specific_mid_prices = get_specific_mid_prices(desired_assets)


btc_mid_price = float(specific_mid_prices.get('BTC'))
eth_mid_price = float(specific_mid_prices.get('ETH'))
eth_mid_price = round(float(f"{eth_mid_price:.5g}"), 6)
sol_mid_price = float(specific_mid_prices.get('SOL'))


def get_random_time(min_time, max_time):
    return random.randint(min_time, max_time)

def get_random_num(min, max):
    return round(random.uniform(min, max), 3)

# User specified range for holding a position (converted from min to seconds)
hold_time = get_random_time(MIN_HOLD_TIME, MAX_HOLD_TIME) #* 60


def place_market_order(account, api_key, coin, buyOrSell, size, delay, revBuyOrSell):
    # Load configuration (e.g., API keys)
    # config = utils.get_config()
    # Create an Ethereum account object from the secret key
    account: LocalAccount = eth_account.Account.from_key(api_key)

    print("Running with account:", account.address)

    # Initialize the Exchange object
    exchange = Exchange(account, constants.MAINNET_API_URL)

    # Define the order parameters
    coin = config["coin"]
    is_buy = buyOrSell  # True for buying, False for selling
    sz = size  # Order size
    if (coin == 'ETH'):
        price = eth_mid_price
    elif (coin == 'BTC'):
        price = btc_mid_price
    elif (coin == 'SOL'):
        price = sol_mid_price
    else:
        print("Please enter valid ticker in config file")
        exit()

    

    # Place a limit open order
    print(f"Attemping to Limit {'Buy' if is_buy else 'Sell'} {sz} {coin}.")
    #order_result = exchange.market_open(coin, is_buy, sz, price, 0.08)
    order_result = exchange.order(coin, is_buy, sz, price, order_type={"limit": {"tif": "Gtc"}}, reduce_only=False, cloid=None)
    print("Waiting 30 seconds...")
    time.sleep(30)
    print("Checking order status...")
    
    
    # Check and print the order result
    if order_result["status"] == "ok":
        filled_status = False
        while filled_status == False:
            status = order_result["response"]["data"]["statuses"][0]
            if "resting" in status:
                print("Re-sending order... (30s)")
                new_price = float(specific_mid_prices.get('ETH'))
                new_price = round(float(f"{new_price:.5g}"), 6)
                oid = status["resting"]["oid"]
                exchange.cancel(coin, oid)
                #need to add current position value in order to re-adjust sz
                order_result = exchange.order(coin, is_buy, sz, new_price, order_type={"limit": {"tif": "Gtc"}}, reduce_only=False, cloid=None)
                time.sleep(25)
            else:
                filled_status = True

                for status in order_result["response"]["data"]["statuses"]:
                    try:
                        filled = status["filled"]
                        print(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
                    except:
                        print(f'Error: {status["error"]}')
    else:
        exit()

    # Wait for specified delay before closing the order (need to make this its own function in order to sync the orders)
    print("We wait for", delay, "seconds before closing")
    exchange.session.close()
    time.sleep(delay)

    # Re-initialize? 
    exchange = Exchange(account, constants.MAINNET_API_URL)
    #exchange.session = requests.Session()

    # Place a market close order
    print(f"We try to Market Close all {coin}.")

    px = exchange._slippage_price(coin, revBuyOrSell, 0.08, None)
    order_result = exchange.order(coin, revBuyOrSell, sz, px, order_type={"limit": {"tif": "Ioc"}}, reduce_only=True)

    if order_result["status"] == "ok":
        for status in order_result["response"]["data"]["statuses"]:
            try:
                filled = status["filled"]
                print(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
            except KeyError:
                print(f'Error: {status["error"]}')
    
    
    





# Hedge trading logic
current_volume = 0
positionSizeOne = get_random_num(config["position_size1_range_min"], config["position_size1_range_max"])
positionSizeTwo = get_random_num(config["position_size2_range_min"], config["position_size2_range_max"])



def main():
    
    #current_volume_usd = 0

#while current_volume_usd < TARGET_VOLUME:

    # User specified range for making a new market order (converted from min to seconds)
    order_freq = get_random_time(MIN_ORDER_FREQ, MAX_ORDER_FREQ) #* 60  # Convert to seconds

    

    
    def loopMain(account, api_key, coin, buyOrSell, size, delay, revBuyOrSell):
        
        while current_volume < TARGET_VOLUME:
            global positionSizeOne 
            positionSizeOne = get_random_num(config["position_size1_range_min"], config["position_size1_range_max"])
            place_market_order(account, api_key, coin, buyOrSell, size, delay, revBuyOrSell)
            #current_volume = config["position_size1"] + current_volume
            #current_volume_usd = current_volume * eth_mid_price
            time.sleep(order_freq)
        print("Volume quota of", TARGET_VOLUME, " has been met!")

    def loopTwo(account, api_key, coin, buyOrSell, size, delay, revBuyOrSell):
        global current_volume
        global hold_time
        while current_volume < TARGET_VOLUME:
            global positionSizeTwo 
            positionSizeTwo = get_random_num(config["position_size1_range_min"], config["position_size1_range_max"])
            place_market_order(account, api_key, coin, buyOrSell, size, delay, revBuyOrSell)
            #current_volume = config["position_size1"] + current_volume
            #current_volume_usd = current_volume * eth_mid_price
            current_volume = positionSizeTwo + current_volume
            print("Current volume = $", current_volume * eth_mid_price)
            hold_time = get_random_time(MIN_HOLD_TIME, MAX_HOLD_TIME)
            time.sleep(order_freq)
            print("We wait", order_freq, "seconds before placing new order")
        print("Volume quota of", TARGET_VOLUME, " has been met!")

    # thread1 = threading.Thread(target=place_market_order, args=(account_1, config["account_1_api_key"], config["coin"], True, config["position_size1"], hold_time, False))
    #  thread2 = threading.Thread(target=place_market_order, args=(account_2, config["account_2_api_key"], config["coin"], False, config["position_size2"], hold_time, True))
    
    thread1 = threading.Thread(target=loopMain, args=(account_1, config["account_1_api_key"], config["coin"], True, positionSizeOne, hold_time, False))
    thread2 = threading.Thread(target=loopTwo, args=(account_2, config["account_2_api_key"], config["coin"], False, positionSizeTwo, hold_time, True))

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    # current_volume = config["position_size1"] + current_volume
    # current_volume_usd = current_volume * eth_mid_price

    #  print("Current volume = $", current_volume_usd)

    #place_market_order(account_1, config["account_1_api_key"], config["coin"], True, config["position_size1"], hold_time)
    #place_market_order(account_2, config["account_2_api_key"], config["coin"], False, config["position_size2"], hold_time)


    
   # time.sleep(order_freq)

    



if __name__ == "__main__":
    main()