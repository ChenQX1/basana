import hashlib
import requests
from typing import Dict
import urllib
import urllib.parse
import urllib.request


class CoinWAPI:
    BASE_URL = "https://api.coinw.com"

    def __init__(self, api_key: str, secret_key: str):
        self.api_key = api_key
        self.secret_key = secret_key

    def _sign_request_spot(self, params: Dict, endpoint: str) -> str:
        params["api_key"] = self.api_key
        sorted_params = sorted(params.items(), key=lambda d: d[0], reverse=False)
        query_string = "&".join([f"{k}={v}" for k, v in sorted_params]).strip()
        query_string = "&".join([query_string, f"secret_key={self.secret_key}"]).strip(
            "&"
        )

        input_name = hashlib.md5()
        input_name.update(query_string.encode("utf-8"))
        sign = input_name.hexdigest().upper()

        encode_params = urllib.parse.urlencode(params)

        url = f"{self.BASE_URL}{endpoint}&sign={sign}&{encode_params}".strip(" &")

        return url

    def _make_request(self, method: str, endpoint: str, params: Dict = {}) -> Dict:
        url = self._sign_request_spot(params, endpoint)
        headers = {"Content-Type": "application/json"}

        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params={})
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, params={})
        else:
            raise ValueError(f"Unsupported method: {method}")

        return response.json()
