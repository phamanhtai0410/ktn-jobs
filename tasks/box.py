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

db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']

NftsModel = db['nfts']
NftsHistoryModel = db['nfts_history']
NftsStatisticsModel = db['nfts_statistics']
NftDetailsModel = db['nft_details']


@worker.task(name='worker.on_created_box', rate_limit='1000/s')
def on_created_box(_event):
    try:
        event = json.loads(_event)
        _to_public_address = py_.get(event, 'args.to', '').lower()
        _tx_hash = py_.get(event, 'transactionHash').lower()
        _token_id = py_.get(event, 'args.tokenId')
        _contract = py_.get(event, 'address').lower()
        _token_detail = py_.get(event, 'args.details')
        _event_name = py_.get(event, 'event')
        _block_number = py_.get(event, 'blockNumber')
        _block_time = py_.get(event, 'block_time')
        _box_index = _token_detail[1]
        _price = _token_detail[2]
        _price = web3.Web3.fromWei(_price, 'ether')
        _is_opened = _token_detail[3]
        _extra_data = py_.get(event, 'extra_data', {})

        _nft_history = NftsHistoryModel.find_one({
            'token_id': _token_id,
            'event': _event_name,
            'tx_hash': _tx_hash
        })

        if _nft_history:
            return f'DONE - Box TokenCreated log existed: {_event}'

        _insert_result = NftsHistoryModel.insert_one({
            **_extra_data,
            'contract': _contract,
            'from_address': str(web3.constants.ADDRESS_ZERO),
            'to_address': _to_public_address,
            'token_id': _token_id,
            'event': _event_name,
            'tx_hash': _tx_hash,
            'block_number': _block_number,
            'block_time': _block_time,
            'created_time': dt_utcnow(),
            'created_by': 'nft_worker'
        })

        NftsModel.find_one_and_update({
            'token_id': _token_id,
            'contract': _contract,
        },
            {
                '$set': {
                    **_extra_data,
                    'token_id': _token_id,
                    'address': _to_public_address,
                    'contract': _contract,
                    'box_index': _box_index,
                    'is_opened': _is_opened,
                    'price': _price,
                    'created_by': 'nft_worker',
                    'created_time': dt_utcnow(),
                }}, upsert=True)

        return f"DONE - insert nft info: {_event}"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_token_created: {_event}"


@worker.task(name='worker.on_transfer_box', rate_limit='1000/s')
def on_transfer_box(_event):
    try:
        event = json.loads(_event)
        _from_public_address = py_.get(event, 'args.from', '').lower()
        _to_public_address = py_.get(event, 'args.to', '').lower()
        _token_id = py_.get(event, 'args.tokenId')
        _event_name = py_.get(event, 'event')
        _tx_hash = py_.get(event, 'transactionHash').lower()
        _block_number = py_.get(event, 'blockNumber')
        _block_time = py_.get(event, 'block_time')
        _contract = py_.get(event, 'address').lower()
        _extra_data = py_.get(event, 'extra_data', {})

        # NOTE: if not mint event will not execute anything
        if _from_public_address == web3.constants.ADDRESS_ZERO:
            return 'DONE - BOX not execute logic with mint action'

        nft_history = NftsHistoryModel.find_one({
            'tx_hash': _tx_hash,
            'token_id': _token_id,
            'event': _event_name
        })

        if nft_history:
            return f'DONE - BOX {_event_name} existed: {_event}'

        NftsHistoryModel.insert_one({
            **_extra_data,
            'contract': _contract,
            'from_address': _from_public_address,
            'to_address': _to_public_address,
            'token_id': _token_id,
            'event': _event_name,
            'tx_hash': _tx_hash,
            'block_number': _block_number,
            'block_time': _block_time,
            'created_time': dt_utcnow(),
            'created_by': 'nft_worker'
        })
        
        NftsModel.find_one_and_update({
            'token_id': _token_id,
            'contract': _contract,
        }, {
            '$set': {
                'old_address': _from_public_address,
                'address': _to_public_address,
                'updated_by': 'nft_worker',
                'updated_time': dt_utcnow()
            }}, upsert=True)

        return f"DONE - BOX update owner box info: {_event}"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - BOX on_transfer_box: {_event}"


@worker.task(name='worker.on_open_box', rate_limit='1000/s')
def on_open_box(_event):
    try:
        event = json.loads(_event)
        _from_public_address = py_.get(event, 'args.from', '').lower()
        _to_public_address = py_.get(event, 'args.to', '').lower()
        _token_id = py_.get(event, 'args.tokenId')
        _event_name = py_.get(event, 'event')
        _tx_hash = py_.get(event, 'transactionHash').lower()
        _block_number = py_.get(event, 'blockNumber')
        _block_time = py_.get(event, 'block_time')
        _contract = py_.get(event, 'address').lower()
        _extra_data = py_.get(event, 'extra_data', {})

        nft_history = NftsHistoryModel.find_one({
            'tx_hash': _tx_hash,
            'token_id': _token_id,
            'event': _event_name
        })

        if nft_history:
            return f'DONE - {_event_name} existed: {_event}'

        NftsHistoryModel.insert_one({
            **_extra_data,
            'contract': _contract,
            'from_address': _from_public_address,
            'to_address': _to_public_address,
            'token_id': _token_id,
            'event': _event_name,
            'tx_hash': _tx_hash,
            'block_number': _block_number,
            'block_time': _block_time,
            'created_time': dt_utcnow(),
            'created_by': 'nft_worker'
        })
        
        NftsModel.find_one_and_update({
            'token_id': _token_id,
            'contract': _contract,
        }, {
            '$set': {
                'is_opened': True,
                'updated_by': 'nft_worker',
                'updated_time': dt_utcnow()
            }}, upsert=True)

        return f"DONE - update owner box info: {_event}"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_transfer_box: {_event}"
