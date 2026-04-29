import re
from urllib.parse import urlparse, urldefrag, urljoin
import utils
from bs4 import BeautifulSoup
import json

# account for traps such as ml libraries and crawlers
# dotn include stop words when counting words
# look into beautiful soup?
# can ignore errors: 601, 602
# important errors: 603, 604, 605


'''
REPORT STRUCTURE (json):
{
unique_pages: set()
longest_page: {"url": "", "count": 0}
word_frequencies: defaultdict(int)
subdomain_pages: defaultdict(set)
}
'''


STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "aren't", "as", "at", "be", "because", "been",
    "before", "being", "below", "between", "both", "but", "by", "can't",
    "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from",
    "further", "get", "got", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't",
    "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't",
    "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over",
    "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should",
    "shouldn't", "so", "some", "such", "than", "that", "that's", "the",
    "their", "theirs", "them", "themselves", "then", "there", "there's",
    "these", "they", "they'd", "they'll", "they're", "they've", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was",
    "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
    "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "will", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
    "you've", "your", "yours", "yourself", "yourselves"
}

def parse_page_content(soup, url, report): # NOTE: Fixed to handle only real, visible text

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text_content = soup.get_text(separator=" ")
    words = re.findall(r"[a-zA-Z]{2,}", text_content.lower())
    
    if len(words) > report["longest_page"]["count"]:
        report["longest_page"]["url"] = url
        report["longest_page"]["count"] = len(words)
    for word in words:
        if word not in STOP_WORDS:
            if word in report["word_frequencies"]:
                report["word_frequencies"][word] += 1
            else: 
                report["word_frequencies"][word] = 1
    
# call in extract_next_links, pass in url in string
def get_subdomain(url: str, report):
    hostname = urlparse(url).hostname
    if hostname and hostname.endswith(".uci.edu"):
        if hostname in report["subdomain_pages"].keys():
            report["subdomain_pages"][hostname] = list(set(report["subdomain_pages"][hostname]).add(url)) # hostname is key, url gets added to the set
        else:
            report["subdomain_pages"][hostname] = [url]

def read_report():
    with open("crawler_report.json", "r", encoding="utf-8") as file:
        report = json.load(file)
    return report

def write_new_report(defragged_url, report, soup):
    #updates report with information from the new url
    report["unique_pages"].append(defragged_url)
    get_subdomain(defragged_url, report)
    parse_page_content(soup, defragged_url, report)

    #every 100 pages, sort word_frequencies
    if len(report["unique_pages"]) % 100 == 0:
        report["word_frequencies"] = dict(sorted(report["word_frequencies"].items(), key=lambda x: -x[1]))

    with open("crawler_report.json", "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)


def print_report():
    report = read_report()
    print(f"Unique pages: {len(report["unique_pages"])}")
    print(f"Longest page: {report["longest_page"]['url']} - {report["longest_page"]['count']} words")
    print("Top 50 words:")
    sorted_words = sorted(report["word_frequencies"].items(), key=lambda x: -x[1])
    for word, count in sorted_words[:50]:
        print(f"{word}: {count}")
    print("Subdomains in uci.edu (alphabetical)")
    for subdomain in sorted(report["subdomain_pages"].keys()):
        print(f"{subdomain}, {len(report["subdomain_pages"][subdomain])}")


def scraper(url, resp) -> list:
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content
    
    # Process only successful responses

    
    if resp.status != 200 or resp.raw_response is None:
        return []
    
    # Skip large pages
    content = resp.raw_response.content
    if len(content) > 5_000_000: 
        return []

    defragged_url = urldefrag(url)[0]
    report = read_report()

    #sets up the json if it's empty
    if not report:
        report = {"unique_pages": list(),
                  "longest_page": {"url": "", "count": 0},
                  "word_frequencies": dict(),
                  "subdomain_pages": dict()
                }

    if defragged_url in report["unique_pages"]:
        return []
    
    #rest only executes if we haven't seen the page yet (url not in unique pages)
    
    try: 
        soup = BeautifulSoup(content, "lxml")
    except:
        soup = BeautifulSoup(content, "html.parser")
    
    write_new_report(defragged_url, report, soup)

    hyperlinks = set()
    
    # code from: https://www.tutorialspoint.com/article/how-can-beautifulsoup-be-used-to-extract-href-links-from-a-website
    for link in soup.find_all('a'):
        absolute = urljoin(resp.raw_response.url, link.get('href'))
        defragged = urldefrag(absolute)[0]
        hyperlinks.add(defragged)
    
    return list(hyperlinks)


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
            re.search(r"/events/(week|month|day|today)", parsed.path.lower()) or
            re.search(r"/events/", parsed.path.lower()) or
            re.search(r"\d{4}/\d{2}/\d{2}", parsed.path) or
            re.search(r"\d{4}-\d{2}-\d{2}", parsed.query.lower()) or
            re.search(r"\d{4}-\d{2}-\d{2}", parsed.path.lower()) or

            re.search(r"doku\.php", parsed.path.lower()) or
            re.search(r"(^|&)(idx|do)=", parsed.query.lower()) or
            re.search(r"(^|&)(subPage|page)=", parsed.query.lower()) or
            
            # dechter
            re.search(r"/~dechter/", parsed.path.lower()) or
            re.search(r"/node\d+\.html$", parsed.path.lower()) or
            
            # trap-heavy hosts 
            host == "grape.ics.uci.edu" or
            host == "flamingo.ics.uci.edu"
        )

        if not allowed or not_allowed :
            return False
        
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1|txt|h|cc|cpp"  # added txt, h, cc, cpp
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

    except TypeError:
        print ("TypeError for ", parsed)
        raise

