import re
from urllib.parse import urlparse, urldefrag
from collections import defaultdict
import utils
from bs4 import BeautifulSoup
import urllib

# account for traps such as ml libraries and crawlers
# dotn include stop words when counting words
# look into beautiful soup?
# can ignore errors: 601, 602
# important errors: 603, 604, 605

unique_pages = set()
longest_page = {"url": "", "count": 0}
word_frequencies = defaultdict(int)
subdomain_pages = defaultdict(set)

def print_report():
    print(f"Unique pages: {len(unique_pages)}")
    print(f"Longest page: {longest_page['url']} - {longest_page['count']} words")
    print("Top 50 words:")
    sorted_words = sorted(word.frequencies.items(), key=lambda x: -x[1])
    for word, count in sorted_words[:50]:
        print(f"{word}: {count}")
    print("Subdomains in uci.edu (alphabetical)")
    for subdomain in sorted(subdomain_pages.keys()):
        print(f"{subdomain}, {len(subdomain_pages[subdomain])}")


def scraper(url: str, resp: utils.response.Response) -> list:
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url: str, resp: utils.response.Response):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    
    if resp.status != 200 or resp.raw_response is None:
        return []
    
    content = resp.raw_response.content
    soup = BeautifulSoup(content, "lxml")
    hyperlinks = []
    for link in soup.find_all('a'):
        hyperlinks.append(link.get('href'))
    
    defragged_url = urldefrag(url)[0]
    unique_pages.add(defragged_url)
    
    return hyperlinks


def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        host = parsed.netloc.lower()
        allowed = (
            host.endswith(".ics.uci.edu") or host == "ics.uci.edu" or
            host.endswith(".cs.uci.edu") or host == "cs.uci.edu" or
            host.endswith(".informatics.uci.edu") or host == "informatics.uci.edu" or
            host.endswith(".stat.uci.edu") or host == "stat.uci.edu"
        )

        not_allowed = (
            # machine learning databases
            re.search(r"/ml", parsed.path.lower()) or
            host.endswith(".archive.ics.uci.edu") or host == "archive.ics.uci.edu" or
            host.endswith(".kdd.ics.uci.edu") or host == "kdd.ics.uci.edu" or

            # calendar/event search
            re.search(r"/events/(week|month|day|today)", parsed.path.lower())
        )

        if not allowed or not_allowed :
            return False
        
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise
