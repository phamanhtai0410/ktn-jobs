# -*- coding: utf-8 -*-
"""
   Description:
        -
        -
"""

import json
import sys

import threading
import time
import traceback
import asyncio
from abc import abstractmethod, ABC
from datetime import datetime
from time import sleep
from typing import Optional, Callable

import sentry_sdk
from hexbytes import HexBytes
from pydash import get
from web3.datastructures import AttributeDict
from web3.middleware import geth_poa_middleware
from rediscluster import RedisCluster

sys.path.append(".")
from util.scan_event import EventScannerState, EventScanner
# from msp_lib.util.logger import Logger

import pydash
from redlock import Redlock
from web3 import Web3

from config import Config
from logger import debug

print(Config.REDIS_CLUSTER)

redis_cluster = RedisCluster(
    startup_nodes=Config.REDIS_CLUSTER,
    decode_responses=True,
    skip_full_coverage_check=True
)
dlm = Redlock(Config.REDLOCK_REDIS, retry_count=2)


# load options
kw_dict = {}
for arg in sys.argv[1:]:
    if '=' in arg:
        sep = arg.find('=')
        key, value = arg[:sep], arg[sep + 1:]
        kw_dict[key] = value


class Provider(object):

    def __init__(self, provider, *args, **kwargs):
        self.rpc = provider
        self.contract = None
        self.web3 = Web3(Web3.HTTPProvider(provider, *args, **kwargs))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)

    def set_contract(self, contract, abi):
        self.contract = self.web3.eth.contract(address=contract, abi=abi)

    def set_handle(self, callback):
        self.callback = callback

    def init_contract(self, contract_address, abi_file):
        self.contract = self.web3.eth.contract(
            address=contract_address, abi=abi_file)

    def get_event_func(self, event):
        return getattr(self.contract.events, event)

    def init_scanner(self, state, event):
        self.scanner = EventScanner(
            web3=self.web3,
            contract=self.contract,
            state=state,
            events=[event],
            filters={
                "address": contract
            },
            max_chunk_scan_size=5000
        )


#
#
# @handle_exception()
# def handle_log(event, wk_handle, provider):
#

class HexJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, HexBytes):
            return obj.hex()
        return super().default(obj)


class RedisState(EventScannerState):
    """Store the state of scanned blocks and all events.

    All state is an in-memory dict.
    Simple load/store massive JSON on start up.
    """

    def __init__(self, address, handle_log, init_block=0, handle_func=''):
        self.state = None
        self.wk_handle = handle_log
        # get and set for each scan event
        self.key_state = f'ktn_cron/scanner:{handle_func}:{address}'
        self.last_save = 0
        self.address = address
        self.init_block = init_block
        self.restore()

    def reset(self, init_block=0):
        if init_block:
            self.init_block = init_block
        """Create initial state of nothing scanned."""
        self.state = {
            "last_scanned_block": self.init_block,
            "blocks": {},
        }
        self.save()

    def restore(self):
        """Restore the last scan state from a file."""
        try:
            _state = redis_cluster.get(self.key_state)
            if _state:
                self.state = json.loads(_state)
            else:
                self.reset(self.init_block)
            # print(f"Restored the state, previously {self.state['last_scanned_block']} blocks have been scanned")
        except (IOError, json.decoder.JSONDecodeError):
            print("State starting from scratch")
            self.reset(self.init_block)

    def save(self):
        """Save everything we have scanned so far in a file."""
        _state = json.dumps(self.state)
        redis_cluster.set(self.key_state, _state)
        # print(f'Ket: {self.key_state}')
        self.last_save = time.time()

    #
    # EventScannerState methods implemented below
    #

    def get_last_scanned_block(self):
        """The number of the last block we have stored."""
        return self.state["last_scanned_block"]

    def delete_data(self, since_block):
        """Remove potentially reorganised blocks from the scan data."""
        for block_num in range(since_block, self.get_last_scanned_block()):
            if block_num in self.state["blocks"]:
                del self.state["blocks"][block_num]

    def start_chunk(self, block_number, chunk_size):
        pass

    def end_chunk(self, block_number):
        """Save at the end of each block, so we can resume in the case of a crash or CTRL+C"""
        # Next time the scanner is started we will resume from this block
        self.state["last_scanned_block"] = block_number

        # Save the database file for every minute
        # if time.time() - self.last_save > 10:
        self.save()

    def process_event(self, block_when: datetime, event: AttributeDict) -> dict:
        try:
            event = json.loads(Web3.toJSON(event))

            _tx_hash = pydash.get(event, 'transactionHash')
            _tx_hash = _tx_hash.lower()
            event['block_time'] = block_when.timestamp()
            event['transactionHash'] = _tx_hash
            if _tx_hash:
                _key = f'msp:msp_redlock\{self.address}:{_tx_hash}'
                _lock = True #dlm.lock(_key, 300000)
                print(f'🔑 🔑 🔑 Key lock: {_key}')
                if _lock:
                    print(
                        f'\033[92m ✔✔✔ Process .................. {_tx_hash} \033[0m')
                    self.wk_handle.delay(json.dumps(event))
                else:
                    print(
                        f'\033[93m ⚠⚠⚠ ______ Lock fail ______ {_tx_hash} \033[0m')
        except:
            sentry_sdk.capture_exception()
            traceback.print_exc()
        return {
            "blockNumber": get(event, "blockNumber")
        }


if __name__ == "__main__":

    contract = kw_dict.get('contract')
    INIT_BLOCK_NUMBER = int(kw_dict.get('from_block', '0'))
    contract = getattr(Config, contract)
    providers = Config.RPC_URIS

    event = kw_dict.get('event')
    abi_path = kw_dict.get('abi_path')
    handle_path = kw_dict.get('handle_path')
    handle_func = kw_dict.get('handle_func')

    # flag for scan all from from_block
    scan_all = int(get(kw_dict, 'scan_all', 1))

    mod = __import__(handle_path)
    _func = getattr(mod, handle_func)

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

    _providers = {}
    # init state scanner
    state = RedisState(address=contract, handle_log=_func, init_block=INIT_BLOCK_NUMBER, handle_func=str(handle_func))
    if not scan_all:
        state.reset(INIT_BLOCK_NUMBER)

    for provider_uri in providers:
        _provider = Provider(provider_uri, request_kwargs={'timeout': 30})
        _provider.init_contract(
            contract_address=contract, abi_file=contract_json)
        # _provider.set_handle(callback=_func)
        _event_func = _provider.get_event_func(event)
        if not _event_func:
            raise Exception(f'Not found event {event}')
        _provider.init_scanner(state, _event_func)
        _providers[provider_uri] = _provider
    chain_reorg_safety_blocks = 10
    # default scanner
    provider_rpc = providers.pop()
    provider = _providers[provider_rpc]
    # provider.scanner.delete_potentially_forked_block_data(state.get_last_scanned_block())
    start_block = None

    while True:
        try:
            # Note that our chain reorg safety blocks cannot go negative 18435731
            print(f'get_last_scanned_block {state.get_last_scanned_block()}')

            start_block = state.get_last_scanned_block()

            end_block = provider.scanner.get_suggested_scan_end_block()


            def _update_progress(start, end, current, current_block_timestamp, chunk_size, events_count):
                if current_block_timestamp:
                    formatted_time = current_block_timestamp.strftime(
                        "%d-%m-%Y")
                else:
                    formatted_time = "no block time available"
                print(
                    f"Current block: {current} ({formatted_time}), blocks in a scan batch: {chunk_size}, events processed in a batch {events_count}")


            print(f"cron log start: {start_block} -> {end_block}")

            result, total_chunks_scanned = provider.scanner.scan(
                start_block,
                end_block,
                progress_callback=_update_progress)
            print(f'done scan {result}')
        except:
            sentry_sdk.capture_exception()
            traceback.print_exc()
            old_rpc = f'{provider_rpc}'
            if not providers:
                print("Cannot switch rpc => retry current rpc")
                sentry_sdk.capture_message(
                    "Cannot switch rpc => retry current rpc")
            else:
                provider_rpc = providers.pop()
                providers.append(old_rpc)
                provider = _providers[provider_rpc]
                sentry_sdk.capture_message(
                    f"switch rpc: from {old_rpc} to {provider_rpc}")
        sleep(60)
