from util.request import RequestUtil
from config import Config

class WalletIAPIUtil:

    @staticmethod
    def add_point(address, amount, ref_id, action='referral_reward'):
        _url_request = f'{Config.WALLET_IAPI}/point'
        _json = {
            'address': address.lower(),
            'amount': amount,
            'ref_id': str(ref_id),
            'action': action
        }

        _response = RequestUtil.post(
            url_request=_url_request,
            json=_json
        )

        print(_response)

        return _response