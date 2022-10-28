import traceback
import pydash as py_
import sentry_sdk
from pymongo import MongoClient
import json
import web3
from util.wallet_iapi import WalletIAPIUtil


from worker import worker
from config import Config
from lib.utils import dt_utcnow

db = MongoClient(Config.MONGO_URI, connect=False)['katana-dapp']

NftDetailsModel = db['nft_details']
ReferralModel = db['referral']
ReferralLogModel = db['referral_log']
ReferralCommissionModel = db['referral_commission']
ReferralCommissionLogModel = db['referral_commission_logs']
SignatureLogsModel = db['signature_logs']
OrderModel = db['orders']
LeaderBoardModel = db['leader_board']


def save_referral_commission(address, ref_code, tx_hash, commission_value, items, event):
    _referral = None
    _is_inc_total_user = False
    _address_linked = None
    if not ref_code:
        # NOTE: if not have ref code on event -> get ref_code in db
        _referral = ReferralModel.find_one({
            'address': address
        })
        _address_linked = py_.get(_referral, 'address_linked', '')
    else:
        _referral = ReferralModel.find_one({
            'code': ref_code
        })

        # NOTE: if referral of this code existed
        if _referral:
            _referral_log = ReferralLogModel.find_one({
                'address': address,
                'code_linked': ref_code
            })
            
            # NOTE: if user not link to this ref code -> replace ref code of user and use this ref_code's address for calculate commission
            if not _referral_log:
                _is_inc_total_user = True

                _address_linked = py_.get(_referral, 'address')

                ReferralLogModel.insert_one({
                    'address': address,
                    'code_linked': ref_code,
                    'address_linked': _address_linked,
                    'created_by': 'worker',
                    'created_time': dt_utcnow()
                })

                ReferralModel.update_one({
                    'address': address
                }, {
                    '$set': {
                        'address': address,
                        'code_linked': ref_code,
                        'address_linked': _address_linked
                    }
                }, upsert=True)
            else:
                #NOTE: if user linked to this ref code -> use this address for calculate commission
                _address_linked = py_.get(_referral_log, 'address_linked')

    _commission_data = {
        'address': _address_linked,
        'updated_by': 'worker',
        'updated_time': dt_utcnow()
    }
    _commission_inc = {
        'commission': commission_value
    }
    if _is_inc_total_user:
        _commission_inc = {
            **_commission_inc,
            'total_user': 1
        }

    _referral_commission_log = ReferralCommissionLogModel.insert_one({
        'tx_hash': tx_hash,
        'commission': commission_value,
        'items': items,
        'address': address,
        'address_linked': _address_linked,
        'referral_code': ref_code,
        'event': event,
        'created_by': 'worker',
        'created_time': dt_utcnow()
    })

    if _address_linked:
        # NOTE: save commission of linked address
        ReferralCommissionModel.find_one_and_update({
            'address': _address_linked
        }, {
            '$set': _commission_data,
            '$inc': _commission_inc
        }, upsert=True)

        LeaderBoardModel.find_one_and_update({
            'address': _address_linked,
            'event': 'top_referral'
        }, {
            '$inc': {
                'point': 1
            },
            '$set': {
                'updated_by': 'worker',
                'updated_time': dt_utcnow()
            }
        }, upsert=True)

        WalletIAPIUtil.add_point(
                address=_address_linked,
                amount=commission_value,
                ref_id=str(_referral_commission_log.inserted_id),
                action='top_referral'
            )

    return


@worker.task(name='worker.on_mint_order_from_dev', rate_limit='1000/s')
def on_mint_order_from_dev(_event):
    event = json.loads(_event)
    _order_id = py_.get(event, 'args.callbackData', '')
    _tx_hash = py_.get(event, 'transactionHash').lower()

    _commission_log = ReferralCommissionLogModel.find_one({
        'tx_hash': _tx_hash
    })
    if _commission_log:
        return f'DONE - on_mint_order_from_dev commission existed: {_event}'

    _order = OrderModel.find_one({
        'order_id': _order_id
    })

    if not _order:
        return 'DONE - on_mint_order_from_dev: not found order_id'

    _ref_code = py_.get(_order, 'ref_code', '')
    _items = py_.get(_order, 'items', [])
    _address = py_.get(_order, 'address')
    _commission_items = []
    _commission_value = 0
    for item in _items:
        _price_after_discount = py_.get(item, 'price_after_discount', 0)
        _commission_percent = py_.get(item, 'commission', 0)
        _commission_item_value =  _commission_percent * _price_after_discount / 100
        _commission_value += _commission_item_value
        _commission_items.append({
            **item,
            'commission_value': _commission_item_value
        })

    save_referral_commission(address=_address, ref_code=_ref_code, tx_hash=_tx_hash, \
        commission_value=_commission_value, items=_commission_items, event=event)

    return f'DONE - on_mint_order_from_dev: {_event} '


@worker.task(name='worker.on_mint_order_from_dapp_creator', rate_limit='1000/s')
def on_mint_order_from_dapp_creator(_event):
    event = json.loads(_event)
    _log_id = py_.get(event, 'args.callbackData', '')
    _tx_hash = py_.get(event, 'transactionHash').lower()

    _commission_log = ReferralCommissionLogModel.find_one({
        'tx_hash': _tx_hash
    })
    if _commission_log:
        return f'DONE - on_mint_order_from_dev commission existed: {_event}'

    _signature_log = SignatureLogsModel.find_one({
        'log_id': _log_id
    })

    if not _signature_log:
        return 'DONE - on_mint_order_from_dapp_creator: signature log not found'

    _ref_code = py_.get(_signature_log, 'ref_code', '')

    _items = py_.get(_signature_log, 'items', [])
    _address = py_.get(_signature_log, 'address')
    _commission_items = []
    _commission_value = 0
    for item in _items:
        _price_after_discount = py_.get(item, 'price_after_discount', 0)
        _commission_percent = py_.get(item, 'commission_percent', 0)
        _commission_item_value =  _commission_percent * _price_after_discount / 100
        _commission_value += _commission_item_value
        _commission_items.append({
            **item,
            'commission_value': _commission_item_value
        })

    save_referral_commission(address=_address, ref_code=_ref_code, tx_hash=_tx_hash, \
        commission_value=_commission_value, items=_commission_items, event=event)

    return f'DONE - on_mint_order_from_dapp_creator: {_event}'
