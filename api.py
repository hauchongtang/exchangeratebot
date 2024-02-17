import requests

BASEURL = 'https://api.freecurrencyapi.com/v1/'


def get_latest_exchange_rates(base_currency='SGD'):
    response = requests.get(f"{BASEURL}latest", params={
        'apikey': 'fca_live_a5aR6daeZAvYvkQF5DN2u1tyBO8tZUsQsqwiW4pC',
        'base_currency': base_currency
    })

    return response.json()
