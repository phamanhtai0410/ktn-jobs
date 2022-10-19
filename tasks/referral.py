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

ReferralRewardConfigModel = db['referral_reward_config']
ReferralRewardLogModel =  db['referral_reward_log']
ReferralModel = db['referral']
NftDetailModel = db['nft_details']
UserModel = db['user']

@worker.task(name='worker.send_referral_reward', rate_limit='1000/s')
def send_referral_reward(origin_id, address, nft_data, reward_type = 'TokenCreated'):
    def calculate_referral_reward(nft_type, rarity):
        _referral_reward_config = ReferralRewardConfigModel.find_one({
            'nft_type': nft_type,
            'rarity': rarity
        })
        if not _referral_reward_config:
            return 0

        _nft_detail = NftDetailModel.find_one({
            'rarity': rarity,
            'type': nft_type
        })

        if not _nft_detail:
            return 0

        _price = py_.get(_nft_detail, 'price', 0)
        _reward_percent = py_.get(_referral_reward_config, 'reward_percent', 0)
        return _price * _reward_percent / 100

    try:
        _token_id = py_.get(nft_data, 'token_id')
        _rarity = py_.get(nft_data, 'rarity')
        _nft_type = py_.get(nft_data, 'nft_type')
        _tx_hash = py_.get(nft_data, 'tx_hash')
        if not _token_id or not _rarity or not _nft_type or not _tx_hash:
            sentry_sdk.capture_message(f'FAIL - not found info of referral reward of {address} for {nft_data}')
            return f'FAIL - not found info of referral reward of {address} for {nft_data}'

        _referral_reward_log = ReferralRewardLogModel.find_one({
            'nft_data.tx_hash': _tx_hash,
            'nft_data.token_id': _token_id
        })

        if _referral_reward_log:
            return 'DONE - send_referral_reward referral reward handled'
        
        _referral = ReferralModel.find_one({
            'address': address
        })
        _address_linked = py_.get(_referral, 'address_linked')
        if not _referral or not _address_linked:
            return f'DONE - send_referral_reward not found referral data - {address}'

        _point = calculate_referral_reward(nft_type=_nft_type, rarity=_rarity)
        
        ReferralRewardLogModel.insert_one({
            'origin_id': origin_id,
            'nft_data': nft_data,
            'address': address,
            'address_linked': _address_linked,
            'point': _point,
            'reward_type': reward_type,
            'created_time': dt_utcnow(),
            'created_by': 'referral_worker'
        })

        if _point > 0:
            UserModel.update_one({
                'address': _address_linked
            }, {
                '$inc': {
                    'total_points': _point
                }
            })

        return f"DONE - send_referral_reward to {_address_linked} for {nft_data}"
    except:
        traceback.print_exc()
        sentry_sdk.capture_exception()
        return f"FAIL - send_referral_reward {address} for {nft_data}"
