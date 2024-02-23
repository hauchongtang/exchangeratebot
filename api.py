import requests
import os

BASEURL = os.environ.get('FREECURRENCY_API_BASE_URL', '')
API_TOKEN = os.environ.get('FREECURRENCY_API_KEY', '')


def get_latest_exchange_rates(base_currency='SGD', currencies=''):
    response = requests.get(f"{BASEURL}latest", params={
        'apikey': API_TOKEN,
        'base_currency': base_currency,
        'currencies': currencies
    })
    return response.json()


def get_supported_currencies():
    response = requests.get(f"{BASEURL}currencies", params={
        'apikey': API_TOKEN,
    })
    return response.json()


valid_currencies = get_supported_currencies()['data']


def get_historical_data(base_currency: str = 'SGD', currencies: str = '', date: str = '2023-10-01'):
    response = requests.get(f"{BASEURL}historical", params={
        'apikey': API_TOKEN,
        'date': date,
        'base_currency': base_currency,
        'currencies': currencies
    })
    return response.json()
