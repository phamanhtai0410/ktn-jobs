

import traceback
import requests
import sentry_sdk


class RequestUtil:

    @staticmethod
    def get(url_request, params={}, headers={}):
        try:
            headers = {
                'Content-Type': 'application/json',
                **headers
            }

            response = requests.request(
                method="GET",
                url=url_request,
                headers=headers,
                params=params
            )
            if response.status_code == 200:
                data = response.json()
                return data

        except Exception as e:
            traceback.print_exc()
            sentry_sdk.capture_exception()

        return None

    @staticmethod
    def post(url_request, json={}, headers={}):
        try:
            headers = {
                'Content-Type': 'application/json',
                **headers
            }

            response = requests.request(
                method="POST",
                url=url_request,
                headers=headers,
                json=json
            )

            if response.status_code == 200:
                data = response.json()
                return data

        except Exception as e:
            traceback.print_exc()
            sentry_sdk.capture_exception()

        return None
