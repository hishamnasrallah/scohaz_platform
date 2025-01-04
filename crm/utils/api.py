
import requests
from requests.exceptions import RequestException

def make_api_call(base_url, method, headers=None, body=None, timeout=30):
    try:
        response = requests.request(
            method=method,
            url=base_url,
            headers=headers,
            json=body,
            timeout=timeout
        )
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        return {"error": str(e)}
