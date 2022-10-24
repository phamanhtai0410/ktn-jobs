import sentry_sdk
from util.request import RequestUtil
from config import Config

class WalletIAPIUtil:

    @staticmethod
    def add_point(address, amount, ref_id, action='referral_reward'):
        _url_request = f'{Config.IAPI_WALLET}/point'
        _json = {
            'address': address.lower(),
            'amount': amount,
            'ref_id': str(ref_id),
            'action': action,
            'event': 'referral'
        }

        _response = RequestUtil.post(
            url_request=_url_request,
            json=_json
        )

        if not _response:
            sentry_sdk.capture_message(f"ERROR: send add point for user {address} amount {amount}")

        return _response