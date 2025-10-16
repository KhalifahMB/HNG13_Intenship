import requests


def fetch_cat_fact():
    url = "https://catfact.ninja/fact"
    fallback_fact = "Cats sleep for about 70% of their lives."
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("fact", fallback_fact)
        else:
            return fallback_fact
    except requests.RequestException:
        return fallback_fact
