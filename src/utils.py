# Via https://stackoverflow.com/questions/7160737/how-to-validate-a-url-in-python-malformed-or-not
from urllib.parse import urlparse


def is_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False