import requests

def fetch_translated_text(api_url, article_id):
    """
    Fetches the translated title and content of an article from the given API.

    Parameters:
    - api_url (str): The base URL of the API.
    - article_id (str): The ID of the article to fetch.

    Returns:
    - dict: A dictionary containing 'title' and 'content' of the translated article.
    """
    url = f'{api_url}/articles/{article_id}'

    response = requests.get(url)

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
