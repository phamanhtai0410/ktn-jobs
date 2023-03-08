

import traceback
import pydash as py_
import sentry_sdk
from pymongo import MongoClient
import json
import web3
from constants import Constants

from worker import worker
from config import Config
from lib.utils import dt_utcnow
from extentions import redis_cluster

# db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']

# PricePairsModel = db['price_pairs']

@worker.task(name='worker.on_save_price', rate_limit='1000/s')
def on_save_price(price_data, pairs):
    def filter_price_by_dex(dex_name, price_response):
        _prices = []
    
        if dex_name == 'Kraken_CW' or dex_name == 'Binance_CW' or dex_name == 'Houbi':
            _prices = price_response.get("result").get("rows")
        
        if dex_name == 'Kraken':
            _prices = price_response.get("result")
            
        if dex_name == 'Binance' or dex_name == 'CoinBase' \
            or dex_name == 'KuCoin':
            _prices = price_response.get("data") 
            
        if dex_name == 'Gemini':
            _prices = price_response.get("prices")   
        return _prices
    
    def get_price_pairs_key(symbol):
        return f'katana-dapp.price_pairs/{symbol}'

    def get_price_cmc_key(symbol):
        return f'katana-dapp.price_cmc/{symbol}'
    
    try:
        if not pairs:
            return 'FAIL - pair not found'

        _dex_name = py_.get(price_data, 'name')
        _price_response = py_.get(price_data, 'price_response')
        if _dex_name == "Coingecko":
            _info_price = {
                "source": _dex_name,
                "url_source": py_.get(price_data, 'url'),
                "symbol": py_.get(_price_response, 'symbol'),
                "price": py_.get(_price_response, 'current_price'),
                "updated_time": dt_utcnow().timestamp()
            }
            _key = get_price_cmc_key(symbol=py_.get(_price_response, 'symbol'))
            redis_cluster.set(_key, json.dumps(_info_price))
            return "DONE - on_save_price CMC"
        
        _prices = filter_price_by_dex(dex_name=_dex_name, price_response=_price_response)
        if not _prices:
            sentry_sdk.capture_message(f'on_save_price not found price data')
            return 'FAIL - not found price data'
        _prices = list(filter(lambda x: x['symbol'] in pairs, _prices))
        for price in _prices:
            _price =  {
                "source": _dex_name,
                "url_source": py_.get(price_data, 'url'),
                "symbol": py_.get(price, 'symbol'),
                "price": py_.get(price, 'price'),
                "updated_time": dt_utcnow().timestamp()
            }
            _key = get_price_pairs_key(symbol=py_.get(price, 'symbol'))
            redis_cluster.set(_key, json.dumps(_price))

        return "DONE - on_save_price"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_save_price"