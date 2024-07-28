import requests


def fetch_article(api_url, article_id, api_key):
    """
    Fetches the article content from the given API.

    Parameters:
    - api_url (str): The base URL of the API.
    - article_id (str): The ID of the article to fetch.
    - api_key (str): The API key for authentication.

    Returns:
    - dict: A dictionary containing 'title' and 'content' of the article.
    """
    url = f'{api_url}/articles/{article_id}'
    headers = {'Authorization': f'Bearer {api_key}'}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        result = response.json()
        if 'title' in result and 'content' in result:
            return {
                'title': result['title'],
                'content': result['content']
            }
        else:
            raise KeyError("Expected keys 'title' and 'content' not found in the response.")
    else:
        raise Exception(f"API Error: {response.status_code} {response.text}")
