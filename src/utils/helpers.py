def fetch_data(url, params=None):
    import requests

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def format_balance_data(data):
    formatted_data = {}
    for item in data:
        formatted_data[item['asset']] = item['free']
    return formatted_data

def validate_api_key(api_key):
    if not api_key or len(api_key) < 32:
        raise ValueError("Invalid API key provided.")