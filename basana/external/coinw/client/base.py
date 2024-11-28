import hashlib
import requests
from typing import Dict
import urllib
import urllib.parse
import urllib.request
from time import time
import hmac
import base64


class CoinWAPI:
    BASE_URL = "https://api.coinw.com"

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key

    def _sign_request_spot(self, params: Dict, endpoint: str) -> str:
        params["api_key"] = self.api_key
        sorted_params = sorted(params.items(), key=lambda d: d[0], reverse=False)
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params]).strip(' &')
        query_string = "&".join([query_string, f"secret_key={self.secret_key}"]).strip(
            ' &'
        )

        input_name = hashlib.md5()
        input_name.update(query_string.encode("utf-8"))
        sign = input_name.hexdigest().upper()

        # Note: the secrete key is not included in the params
        # The secrete key is used to generate the sign for spot request
        encode_params = urllib.parse.urlencode(params)
        url = f"{self.BASE_URL}{endpoint}&sign={sign}&{encode_params}".strip(" &")

        return url

    def _sign_request_futures(self, method: str, endpoint: str, params: Dict = {}) -> str:
        timestamp = str(int(time() * 1000))
        
        # Add timestamp and api_key to params
        params['timestamp'] = timestamp
        params['api_key'] = self.api_key
        
        sorted_params = sorted(params.items(), key=lambda d: d[0])
        query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
        string_to_sign = f"{timestamp}{method.upper()}{endpoint}?{query_string}"
        
        sign = hmac.new(self.secret_key.encode(), string_to_sign.encode(), hashlib.sha256).digest()
        sign_ = base64.b64encode(sign).decode()
        url = f"{self.BASE_URL}{endpoint}?{query_string}"
        headers = {
                "timestamp": timestamp,
                "api_key": self.api_key,
                "sign": sign_
            }

        return url, headers

    def _make_request(self, method: str, endpoint: str, params: Dict = {}, is_futures: bool = False) -> Dict:
        if is_futures:
            url, headers = self._sign_request_futures(method, endpoint, params)
        else:
            url = self._sign_request_spot(params, endpoint)
            headers = {"Content-Type": "application/json"}

        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params={})
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, params={})
        else:
            raise ValueError(f"Unsupported method: {method}")

        return response.json()
