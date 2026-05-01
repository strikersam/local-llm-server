import urllib.parse

def read_url(url):
    parsed_url = urllib.parse.urlparse(url)
    return {
        "scheme": parsed_url.scheme,
        "netloc": parsed_url.netloc,
        "path": parsed_url.path,
        "params": parsed_url.params,
        "query": parsed_url.query,
        "fragment": parsed_url.fragment
    }
