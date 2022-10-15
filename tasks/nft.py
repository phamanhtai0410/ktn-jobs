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

db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']

NftsModel = db['nfts']
NftsHistoryModel = db['nfts_history']

@worker.task(name='worker.on_token_created', rate_limit='1000/s')
def on_token_created(_event):
    try:
        event = json.loads(_event)
        _to_public_address = py_.get(event, 'args.to', '').lower()
        _token_id = py_.get(event, 'args.tokenId')
        _contract = py_.get(event, 'address')
        _token_detail = py_.get(event, 'args.details')
        _rarity = _token_detail[0]
        _nft_type = _token_detail[1]
        _token_uri = _token_detail[2]
        _is_used = _token_detail[3]

        
        _nft = NftsModel.find_one({
            'token_id': _token_id
        })
        
        if _nft:
            return 'DONE - token id existed'

        NftsModel.insert_one({
            'token_id': _token_id,
            'address': _to_public_address,
            'contract': _contract,
            'rarity': _rarity,
            'nft_type': _nft_type,
            'is_used': _is_used,
            'token_uri': _token_uri,
            'created_by': 'nft_worker',
            'created_time': dt_utcnow()
        })

        return f"DONE - insert nft info: {_event}"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_token_created: {_event}"



@worker.task(name='worker.on_transfer_nft', rate_limit='1000/s')
def on_transfer_nft(_event):
    try:
        event = json.loads(_event)
        _from_public_address = py_.get(event, 'args.from', '').lower()
        _to_public_address = py_.get(event, 'args.to', '').lower()
        _token_id = py_.get(event, 'args.tokenId')
        _event_name = py_.get(event, 'event')
        _tx_hash = py_.get(event, 'transactionHash')
        _block_number = py_.get(event, 'blockNumber')
        _block_time = py_.get(event, 'block_time')
        _contract = py_.get(event, 'address')
        if _from_public_address == web3.constants.ADDRESS_ZERO:
            _event_name = Constants.EVENT_NAME_TOKEN_CREATED

        nft_history = NftsHistoryModel.find_one({
            'token_id': _token_id,
            'address': _contract
        })

        if nft_history:
            return f'DONE - log existed: {_event}'

        NftsHistoryModel.insert_one({
            'address': _contract,
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
            'address': _from_public_address
        }, {
            '$set': {
                'address': _to_public_address,
                'updated_by': 'nft_worker',
                'updated_time': dt_utcnow()
            }})

        return f"DONE - update owner nft info: {_event}"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - on_transfer_nft: {_event}"
