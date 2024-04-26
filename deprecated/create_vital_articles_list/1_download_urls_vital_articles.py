import requests
from bs4 import BeautifulSoup

vital_articles_url = 'https://en.wikipedia.org/w/index.php?title=Wikipedia:Vital_articles/List_of_all_articles&oldid=928962928'
#vital_articles_url = 'https://en.wikipedia.org/w/index.php?title=Wikipedia:Vital_articles/List_of_all_articles'

ignore_patterns = [
    "/wiki/Special:",
    "/wiki/Wikipedia:",
    "/wiki/Help:",
    "/wiki/Portal:",
    "/wiki/User:",
    "/wiki/User_talk:",
    "/wiki/Category:"
]

ignored_urls = [
    'https://en.wikipedia.org/wiki/Main_Page'
]

def pattern_in_href(href):
    for pattern in ignore_patterns:
        if pattern in href:
            return True
    return False

# return all the links in the page, given the url and the restrictions
def save_links(url):
    response = requests.get(url)
    if response.status_code != 200:
        print("Failed to fetch the webpage")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')

    a_tags = soup.find_all('a', href=True)
    links = []

    for tag in a_tags:
        href = tag['href']
        full_link = 'https://en.wikipedia.org' + href

        if href.startswith('/wiki/') and full_link not in links and not pattern_in_href(href) and not full_link in ignored_urls:
            links.append(full_link)

    return links

links = save_links(vital_articles_url)

with open('vital_articles_2024.txt', 'w') as f:
    for link in links:
        f.write(link + '\n')

print("Links have been saved to vital_articles file.")
