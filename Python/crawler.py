"""
:Module: crawler.py

:Author:
    Peter Hyl

:Description:   This module contains web crawler and image crawler with caching,
                and other necessary function.
"""
import collections
import json
import logging
import os
import re
import sqlite3

from datetime import datetime, timedelta
from hashlib import sha1
from time import time
from urllib.parse import urldefrag, urljoin, urlparse, urlsplit

import bs4
import requests

from basic_functions import initialize_logging, safe_func


class CrawlerCache(object):
    """
    Crawler data caching per relative URL and domain.
    """
    def __init__(self, db_file, refresh=7):
        self.conn = sqlite3.connect(db_file, detect_types=sqlite3.PARSE_DECLTYPES)
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS sites
            (domain text, url text, content text, store_time timestamp)''')
        self.conn.commit()
        self.cursor = self.conn.cursor()
        self.refresh = refresh

    def set(self, domain, url, data):
        """
        Store the content for a given domain and url
        """
        self.cursor.execute("INSERT INTO sites VALUES (?,?,?,?)", (domain, url, data, datetime.now()))
        logging.debug("Cached page: [%s] %s", domain, url)
        self.conn.commit()

    def get(self, domain, url):
        """
        Return the content for a given domain and url
        """
        self.cursor.execute("SELECT content, store_time FROM sites WHERE domain=? and url=?", (domain, url))
        row = self.cursor.fetchall()

        if row:
            if row[0][1] + timedelta(days=self.refresh) < datetime.now():
                self.delete(domain, url)
                return
            return row[0][0]

    def delete(self, domain, url):
        """
        Delete the content for a given domain and url
        """
        self.cursor.execute("DELETE FROM sites WHERE domain=? and url=?", (domain, url))
        logging.debug("Should by delete row: [%s] %s", domain, url)

    def get_urls(self, domain):
        """
        Return all the URLS within a domain
        """
        self.cursor.execute("SELECT url FROM sites WHERE domain=?", (domain,))

        return [row[0] for row in self.cursor.fetchall()]


class HTMLException(Exception):
    """
    Exception for missing and invalid schema and non-HTML content.
    """
    def __init__(self, *args):
        super().__init__(self, *args)


class Crawler(object):
    """
    Class for web crawler that crawls link on page.

    Args:
        cache:          a cache controller (optional)
        max_pages:      maximum number of pages to crawl (optional)
        single_domain:  whether to only crawl links within start page's domain (optional)
    """
    def __init__(self, cache=None, max_pages=50, single_domain=True):

        self.max_pages = max_pages
        self.cache = cache
        self.single_domain = single_domain
        self.domain = None
        self.no_cache = None
        self.sess = requests.session()  # initialize the session

    @safe_func
    def crawl(self, start_page, no_cache=False):
        """
        Crawl the web starting from specified page.

        Args:
            start_page: URL of starting page
            no_cache: function returning True if the url should be refreshed
        """
        pages = 0  # number of pages succesfully crawled
        failed = 0  # number of links that couldn't be crawled
        crawled = []  # list of pages already crawled
        page_queue = collections.deque()  # queue of pages to be crawled
        page_queue.append(start_page)

        self.no_cache = no_cache
        self.domain = urlparse(start_page).netloc if self.single_domain else None

        while page_queue:
            url = page_queue.popleft()  # get next page to crawl (FIFO queue)
            # read the page
            try:
                soup = self.get(url)
            except HTMLException:
                failed += 1
                continue

            # process the page
            crawled.append(url)
            pages += 1
            self.page_handler(url, soup)
            if pages >= self.max_pages:
                logging.info("The maximum number of pages has been reached.")
                break
            # get the links from this page and add them to the crawler queue
            links = self.get_links(url, soup)
            for link in links:
                if not url_in_list(link, crawled) and not url_in_list(link, page_queue):
                    page_queue.append(link)

        logging.info("%d pages crawled, %d links failed.", pages, failed)

    def get_html(self, url):
        """
        Return html page from url as text(string).

        Args:
            url:    URL of page
        """
        try:
            response = self.sess.get(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.InvalidSchema) as exp:
            logging.warning("FAILED: %s", exp)
            raise HTMLException(exp)
        except requests.exceptions.SSLError as exp:
            logging.error("Problem with SSL certificate: %s", exp)
            return
        if not response.headers['content-type'].startswith('text/html'):
            msg = "Don't crawl non-HTML content, url: {}".format(url)
            logging.warning(msg)
            raise HTMLException(msg)

        return response.text

    def get_links(self, url, soup):
        """
        Returns a list of links from from this page to be crawled.

        Args:
            url:    URL of this page
            soup:   BeautifulSoup object for this page
        """
        # get target URLs for all links on the page
        links = [a['href'] for a in soup.select('a[href]')]
        # remove fragment identifiers
        links = [urldefrag(link)[0] for link in links]
        # remove any empty strings
        links = [link for link in links if link]
        # if it's a relative link, change to absolute
        links = [link if bool(urlparse(link).netloc) else urljoin(url, link) for link in links]
        # if only crawling a single domain, remove links to other domains
        if self.domain:
            links = [link for link in links if same_domain(urlparse(link).netloc, self.domain)]

        return links

    def get(self, url):
        """
        Read the page(url) and return parsed html via BeautifulSoup.

        Args:
            url:    URL of page
        """
        if self.is_cacheable():
            response = self.cache.get(self.domain, url)
            if not response:
                response = self.get_html(url)
                self.cache.set(self.domain, url, response)
                soup = bs4.BeautifulSoup(response, "html.parser")
            else:
                logging.debug("Cached url [%s] %s" % (self.domain, url))
                soup = bs4.BeautifulSoup(response, "html.parser")
        else:
            response = self.get_html(url)
            soup = bs4.BeautifulSoup(response, "html.parser")

        return soup

    def is_cacheable(self):
        """
        If exists cache and want use cache (no_cache == False) return true.
        """
        return self.cache and not self.no_cache

    def page_handler(self, url, soup):
        """
        Function to be customized for processing of a single page.

        Args:
            url:    URL of this page
            soup:   Beautiful Soup object created from response
        """
        logging.info('Crawling: %s', url)


class ImageCrawler(Crawler):
    suffix_list = ('.jpg', '.gif', '.png', '.tif', '.svg', '.ico')
    """
    Class for web crawler that crawls link on page and collect images.

    Args:
        cache:              a cache controller (optional)
        max_pages:          maximum number of pages to crawl (optional)
        single_domain:      whether to only crawl links within start page's domain (optional)
        path_images:        path where want store images
        only_tag_images:    if true download only images with tag <img>
    """
    def __init__(self, cache=None, max_pages=50, single_domain=True, path_images=None, only_tag_images=True):
        super().__init__(cache, max_pages, single_domain)
        self.only_tag_images = only_tag_images
        if path_images:
            self.path_images = path_images
        else:
            self.path_images = os.path.join('.', 'images')
        if not os.path.exists(self.path_images):
            os.makedirs(self.path_images)

    def page_handler(self, url, soup):
        """
        Function for download images from current page.

        Args:
            url:    URL of current page
            soup:   Beautiful Soup object created from response
        """
        # call parent page handler for logging
        super().page_handler(url, soup)
        # get target URLs for all image on the page
        images = [a['src'] for a in soup.select('img[src]')]

        if not self.only_tag_images:
            images += [a['href'] for a in soup.findAll('link', {'rel': re.compile('icon')})]
            images += [a['content'] for a in soup.findAll('meta', {'property': re.compile('image')})]
            images += [a['style'].rsplit('\'', 2)[1] for a in soup.findAll('div', {'style': re.compile('image')})]

            snippet = soup.findAll('script', type='application/ld+json')
            data = [json.loads(a.text) for a in snippet]
            images += [a['logo'] for a in data if 'logo' in a]

        # if it's a relative link, change to absolute
        images = [link if bool(urlparse(link).netloc) else urljoin(url, link) for link in images]
        # remove any empty strings
        images = [link for link in images if link]

        logging.info("Stared downloading images.")
        # remove duplicates
        list(set(images))
        for image in images:
            self.download_image(image)
        logging.info("Finished downloading images.")

    def download_image(self, img_url):
        """
        Function download image from URL and check suffix.

        Args:
            img_url:    URL of image to download
        """
        file_name = os.path.join(self.path_images, urlsplit(img_url)[2].split('/')[-1])
        try:
            i = self.sess.get(img_url)
        except (requests.exceptions.MissingSchema, requests.exceptions.InvalidSchema) as exp:
            logging.info("Failed image downloading: %s", exp)
            return
        except requests.exceptions.SSLError as exp:
            logging.error("Problem with SSL certificate: %s", exp)
            return

        if file_name.endswith(self.suffix_list) and i.status_code == requests.codes.ok:
            write_to_file(i.content, file_name)
        else:
            logging.debug("Bad suffix or status code for: %s", img_url)


def write_to_file(data, file_name):
    """
    Write to file, but if this file is exist and same hash like a new return,
    if files have different hash add counter to file name: "file_counter.jpg".

    Args:
        data:       data for writing to file
        file_name:  file name(path to file)
    """
    hash_new = sha1(data)
    count = 0
    new_name = file_name

    while True:
        if not os.path.exists(new_name):
            # when write file return
            with open(new_name, 'wb') as file:
                file.write(data)
            logging.info("Image si store: %s", new_name)
            return
        else:
            with open(new_name, 'rb') as file:
                hash_file = sha1(file.read())
            if hash_new.hexdigest() == hash_file.hexdigest():
                # if file is stored don't rewrite and return
                logging.debug("The image has been downloaded: %s", new_name)
                return
            # create new file name
            new_name, suffix = file_name.rsplit('.', 1)
            new_name = "{}_{}.{}".format(new_name, count, suffix)
            count += 1


def same_domain(netloc1, netloc2):
    """
    Determine whether two netloc values are the same domain.
    This function does a "subdomain-insensitive" comparison. In other words ...
    """
    domain1 = netloc1.lower()
    if '.' in domain1:
        domain1 = domain1.split('.')[-2] + '.' + domain1.split('.')[-1]

    domain2 = netloc2.lower()
    if '.' in domain2:
        domain2 = domain2.split('.')[-2] + '.' + domain2.split('.')[-1]

    return domain1 == domain2


def url_in_list(url, listobj):
    """
    Determine whether a URL is in a list of URLs.
    This function checks whether the URL is contained in the list with either
    an http:// or https:// prefix. It is used to avoid crawling the same
    page separately as http and https.
    """
    http_version = url.replace('https://', 'http://')
    https_version = url.replace('http://', 'https://')
    return (http_version in listobj) or (https_version in listobj)


if __name__ == "__main__":
    initialize_logging(log_file="./crawler.log", level="debug")
    logging.info("Start crawling.")
    START = time()
    crawler = ImageCrawler(CrawlerCache('crawler.db'), max_pages=1, only_tag_images=False)
    crawler.crawl('http://hej.sk/')
    END = time()
    logging.info('Elapsed time (seconds) = ' + str(END-START))
