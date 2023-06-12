import requests


QUERY_TEMPLATE = "https://itunes.apple.com/search?term=%s&media=music&entity=album"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.55 Safari/537.36"


def get_cover_url(song_query, verbose=False, throttle=1):
    url = QUERY_TEMPLATE % song_query
    response = requests.get(url, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()

    data = response.json()["results"]

    if not data:
        return None

    return data[0]["artworkUrl100"].replace("100x100", "1000x1000")


def download_cover(song_query, output_path=None):
    url = get_cover_url(song_query)
    if not url:
        return None

    print(f"Downloading cover from {url}")

    response = requests.get(url, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()

    if not response.content:
        return None

    if not output_path:
        output_path = f"out/cover/{song_query}.jpg"

    else:
        output_path = f"{output_path}/cover.jpg"

    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path
