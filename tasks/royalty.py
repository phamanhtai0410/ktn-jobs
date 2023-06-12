import traceback
import pydash as py_
import sentry_sdk
from pymongo import MongoClient
import json
import web3
from constants import Constants
from tasks.referral import send_referral_reward

from worker import worker
from config import Config
from lib.utils import dt_utcnow
from lib.logger import LoggerTask
from constants import Constants
db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']

RoyaltyWithdrawHistory = db['royalty_withdraw_history']
Royalty = db['royalty']

# python3 schedules/cron_logs.py contract=TREASURY_ROYALTY_CONTRACT from_block=27655697 abi_path=abis/katana_royalty.json handle_path=tasks handle_func=on_withdraw_royalty event=Withdraw scan_all=0
@worker.task(name='worker.on_withdraw_royalty', rate_limit='1000/s')
def on_withdraw_royalty(_event):
    try:
        if isinstance(_event, dict):
            event = _event
        else:   
            event = json.loads(_event)
        _to_public_address = py_.get(event, 'args.receipient', '').lower()
        _amount = py_.get(event, 'args.amount', 0)
        _amount = float(web3.Web3.fromWei(_amount, 'ether'))
        _tx_hash = py_.get(event, 'transactionHash').lower()
        _contract = py_.get(event, 'address').lower()
        # _event_name = py_.get(event, 'event')
        _block_number = py_.get(event, 'blockNumber')
        _block_time = py_.get(event, 'block_time')

        RoyaltyWithdrawHistory.find_one_and_update({
            "tx_hash": _tx_hash,
            "contract": _contract
        },
            {
                '$set': {
                    "tx_hash": _tx_hash,
                    "block_number": _block_number,
                    'block_time': _block_time,
                    "address": _to_public_address,
                    "contract": _contract,
                    "amount": _amount,
                    'created_by': 'royalty_worker',
                    'created_time': dt_utcnow(),
                }}, upsert=True)

        return f"DONE - insert withdraw royalty info: {_event}"
    except Exception as exc:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_withdraw_royalty: {_event}"
    
    
@worker.task(name='worker.on_get_info_royalty', rate_limit='1000/s')
def on_get_info_royalty(_event):
    try:
        if isinstance(_event, dict):
            event = _event
        else:   
            event = json.loads(_event)
        _collection_address = py_.get(event, "collection_address")
        _find_address_royalty = Royalty.find(
            {"collection_address": _collection_address}
        )
        _find_address_royalty = list(_find_address_royalty)        
        if len(_find_address_royalty) == 0:
            return f'Collection in Royalty not found, with info: {_event}'
        
        for _royalty in _find_address_royalty:
            _address = py_.get(_royalty, "user_address")
            _msg_royalty = {
                "collection_address": _collection_address, 
                "user_address": _address,
                "token": Constants.SYMBOL_BNB
            }
            LoggerTask.debug(f"_msg_royalty {_msg_royalty}" )
            on_update_balance_royalty.delay(json.dumps(_msg_royalty))
            _msg_royalty["token"] = Constants.SYMBOL_WBNB
            on_update_balance_royalty.delay(json.dumps(_msg_royalty))
            _msg_royalty["token"] = Constants.SYMBOL_USDT
            on_update_balance_royalty.delay(json.dumps(_msg_royalty))                                         
        return f"DONE - get balance royalty info: {_event}"
    except :
        traceback.print_exc()
        sentry_sdk.capture_exception()       
        return f"FAIL - on_get_info_royalty: {_event}"


@worker.task(name='worker.on_update_balance_royalty', rate_limit='1000/s')
def on_update_balance_royalty(_event):
    try:
        if isinstance(_event, dict):
            event = _event
        else:   
            event = json.loads(_event)
        _collection_address = py_.get(event, "collection_address")
        _user_address = py_.get(event, "user_address")
        _symbol = py_.get(event, "token")
        
        if _symbol == Constants.SYMBOL_BNB:
            _contract_address = "" # native token
        elif _symbol == Constants.SYMBOL_WBNB:
            _contract_address = Config.TOKEN_WBNB
        elif _symbol == Constants.SYMBOL_USDT:
            _contract_address = Config.TOKEN_USDT
        else:
            return f'token does not support: {_event}'
        
        _web3 = web3.Web3(web3.Web3.HTTPProvider(Config.RPC_URIS[0]))
        with open('abis/IERC20.json') as file:
            contract_json = json.load(file)
        if not contract_json:
            raise Exception(f'Not found file abi abis/IERC20.json')
        _check_sum_user_address = web3.Web3.toChecksumAddress(_user_address)
        
        if _contract_address == "":
            _balance = _web3.eth.getBalance(_check_sum_user_address)
        else:
            _token_erc20 = _web3.eth.contract(address=_contract_address, abi=contract_json)
            _balance = _token_erc20.functions.balanceOf(_check_sum_user_address).call()
        _balance = float(web3.Web3.fromWei(_balance, 'ether'))
        
        Royalty.update_one(
            { 
                "user_address": _user_address,
                "collection_address": _collection_address
            },
            { "$pull": { "balances": {"symbol": _symbol }}} # remove object with symbol
        )
        Royalty.update_one(
            {
                "user_address": _user_address,
                "collection_address": _collection_address
            },
            { 
                "$push": {"balances": {"balance": _balance, "symbol": _symbol}}
            }
        )
        
        return f"DONE - update balance royalty success : {_event}, balance: {_balance}"
    except Exception as exc:
        raise exc
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_update_balance_royalty: {_event}"
    


