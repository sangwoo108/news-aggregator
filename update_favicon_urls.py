import requests
import glob
from multiprocessing import Pool, cpu_count
from typing import List, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
from config import FAVICON_LOOKUP_FILE, CONCURRENCY
from utils import ensure_scheme, get_all_domains

# In seconds. Tested with 5s but it's too low for a bunch of sites (I'm looking
# at you https://skysports.com).
REQUEST_TIMEOUT = 15

def get_favicon(domain: str) -> Tuple[str, str]:
    # Only sources from the Japanese file include a scheme, so parse the domain
    # as a url to get something we can use in a http request.
    domain = ensure_scheme(domain)

    # Set the default favicon path. If we don't find something better, we'll use
    # this.
    icon_url = '/favicon.ico'

    try:    
        response = requests.get(domain, timeout=REQUEST_TIMEOUT, headers={
            'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Mobile Safari/537.36'
        })
        soup = BeautifulSoup(response.text, features='lxml')
        icon = soup.find('link', rel="shortcut icon")

        # Check if the icon exists, and the href is not empty. Surprisingly,
        # some sites actually do this (https://coinchoice.net/ + more).
        if icon and icon.get('href'):
            icon_url = icon.get('href')
    except Exception as e:
        print(f'Failed to download HTML for {domain}. Using default icon path {icon_url}', e)

    # We need to resolve relative urls so we send something sensible to the client.
    icon_url = urljoin(domain, icon_url)
    return (domain, icon_url)

if __name__ == "__main__":
    domains = list(get_all_domains())
    print(f"Processing {len(domains)} domains")

    favicons: List[Tuple[str, str]]
    with Pool(CONCURRENCY) as p:
        favicons = p.map(get_favicon, domains)

    # This isn't sent over the network, so format it nicely.
    result = json.dumps(dict(favicons), indent=4)
    with open(f'{FAVICON_LOOKUP_FILE}.json', 'w') as f:
        f.write(result)

    print("Done!")
