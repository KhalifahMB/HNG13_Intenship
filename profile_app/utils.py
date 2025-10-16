import requests
from requests.exceptions import RequestException, Timeout


def fetch_cat_fact(timeout: float = 5.0):
    url = "https://catfact.ninja/fact"

    try:
        resp = requests.get(url, timeout=timeout)
    except Timeout:
        return ("Cat Facts API request timed out.", 504)
    except RequestException:
        return ("Unable to reach Cat Facts API.", 503)

    if resp.status_code != 200:
        return (resp.text, resp.status_code)

    data = resp.json()
    fact = data.get("fact")
    return (fact, resp.status_code)
