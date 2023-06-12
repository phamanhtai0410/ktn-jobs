# -*- coding: utf-8 -*-

"""
   Description:
        -
        -
"""

import json
import sys
import traceback
import asyncio
from datetime import datetime, timezone

import sentry_sdk
from bson import ObjectId
from pydash import get
from rediscluster import RedisCluster
from redlock import Redlock

sys.path.append(".")

from util import logger
from util import make_red_key
# import tasks.workers as workers
import pydash
from web3 import Web3
from config import Config


if Config.SENTRY_DSN:
    sentry_sdk.init(Config.SENTRY_DSN)
redis_cluster = RedisCluster(
    startup_nodes=Config.REDIS_CLUSTER,
    decode_responses=True,
    skip_full_coverage_check=True
)
dlm = Redlock(Config.REDLOCK_REDIS, retry_count=2)

def dt_utcnow():
    return datetime.utcnow().replace(tzinfo=timezone.utc)

class Provider(object):

    def __init__(self, provider, *args, **kwargs):
        self.contract = None
        self.web3 = Web3(Web3.HTTPProvider(provider, *args, **kwargs))

    def set_contract(self, contract, abi):
        self.contract = self.web3.eth.contract(address=contract, abi=abi)

def handle_event(event, wk_handle, provider):
    try:
        print("test thu ")
        _event = Web3.toJSON(event)
        _json = json.loads(_event)
        _json['transactionHash'] = _json['transactionHash'].lower()

        _tx_hash = pydash.get(_json, 'transactionHash')

        logger.debug(f'[EVENT] event')
        logger.debug(f'{_tx_hash}')
        if _tx_hash:

            _key = make_red_key(
                tx_hash=_tx_hash,
                contract=pydash.get(_json, 'address').lower()
            )

            _lock = dlm.lock(_key, 60 * 5)
            logger.debug(f'[EVENT] 🔑 🔑 🔑 Key lock: {_key}')

            if _lock:
                logger.debug(f'[EVENT] \033[92m ✔✔✔ Process .................. {provider} \033[0m')
                wk_handle.delay(_json)
            else:
                logger.debug(f'[EVENT] \033[93m ⚠⚠⚠ ______ Lock fail ______ {provider} \033[0m')

    except:
        sentry_sdk.capture_exception()
        traceback.print_exc()


class EventListener():

    def __init__(self, provider, *args, **kwargs):
        # threading.Thread.__init__(self)
        self.contract_address = None
        self.callback = None
        self.event = None
        self.contract = None
        self.provider = provider
        self.web3 = Web3(Web3.HTTPProvider(provider, *args, **kwargs)) 

    def set_handle(self, event, callback):
        self.event = event
        self.callback = callback

    def init_contract(self, contract_address, abi_file):
        self.contract_address = contract_address
        self.contract = self.web3.eth.contract(address=Web3.toChecksumAddress(contract_address), abi=abi_file)

    def run(self, auto_remove_at=0) -> None:
        # asynchronous defined function to loop
        # this loop sets up an event filter and is looking for new entires for the "PairCreated" event
        # this loop runs on a poll interval

        async def log_loop(event_filter, poll_interval, callback, provider):
            while True:
                for evt in event_filter.get_new_entries():
                    try:
                        handle_event(evt, callback, provider)
                    except Exception as e:
                        print(e)
                        print('Error', provider)
                        traceback.print_exc()
                await asyncio.sleep(poll_interval)

        _run = True
        while _run:
            try:
                logger.debug(f'[EVENT] Start {"**" * 5} {self.contract_address} {self.event}')

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                _lastBlock = 'latest'
                try:
                    _event_func = getattr(self.contract.events, self.event)
                    event_filter = _event_func.createFilter(
                        fromBlock='latest'
                    )
                    logger.debug(f"[EVENT]  Start listening to event {_event_func} ... {event_filter}")
                    loop.run_until_complete(
                        asyncio.gather(
                            log_loop(event_filter, 2, self.callback, self.provider)
                        ))
                except Exception as e:
                    traceback.print_exc()
                finally:
                    loop.close()
                if auto_remove_at and dt_utcnow().timestamp() > auto_remove_at:
                    _run = False
            except:
                traceback.print_exc()


def run_listener(**kwargs):
    providers = Config.RPC_URIS
    contract = kwargs['contract']
    event = kwargs['event']
    abi_path = kwargs['abi_path']
    handle_func = kwargs['handle_func']
    handle_path = kwargs['handle_path']
        
    logger.debug(f'[EVENT]  {"**" * 5} Start Event')
    logger.debug(f'[EVENT]  {"**" * 5}  {contract}  {event}')

    mod = __import__(handle_path)
    _func = getattr(mod, handle_func)
    print("_func ", _func)
    with open(abi_path) as file:
        contract_json = json.load(file)

    if not _func:
        raise Exception(f"Not found function {handle_func} {handle_func}")
    if not contract_json:
        raise Exception(f'Not found file abi {abi_path}')
    if not providers:
        raise Exception(f"Not found RPC_URIS config")
    if not contract:
        raise Exception(f"Not found config for: {kw_dict.get('contract')}")

    _providers = []
    for provider_uri in providers:
        _provider = EventListener(provider_uri, request_kwargs={'timeout': 30})
        _provider.init_contract(contract_address=contract, abi_file=contract_json)
        _provider.set_handle(event=event, callback=_func)
        _providers.append(_provider)
    _providers[0].run(auto_remove_at=get(kwargs, 'auto_remove_at', 0))


kw_dict = {}
for arg in sys.argv[1:]:
    if '=' in arg:
        sep = arg.find('=')
        key, value = arg[:sep], arg[sep + 1:]
        kw_dict[key] = value

# python3 listener.py contract=TREASURY_ROYALTY_CONTRACT abi_path=abis/katana_royalty.json handle_path=tasks handle_func=on_withdraw_royalty event=Withdraw
if __name__ == "__main__":
    contract = kw_dict.get('contract')
    contract = getattr(Config, contract)
    event = kw_dict.get('event')
    abi_path = kw_dict.get('abi_path')
    handle_path = kw_dict.get('handle_path')
    handle_func = kw_dict.get('handle_func')
    parse_event = int(get(kw_dict, 'parse_event', 0))
    info_job = {
        "contract": contract,
        "event": event,
        "abi_path": abi_path,
        "handle_path": handle_path,
        "handle_func": handle_func,
        "parse_event": parse_event
    }
    try:
        run_listener(**info_job)
    except:
        sentry_sdk.capture_exception()
        traceback.print_exc()
    
