"""
:Module: shopify_crawler.py

:Author:
    Peter Hyl

:Description:   This module contains web crawler and other necessary function which
                from input csv file load shopify urls to crawl. Collecting  emails,
                facebook, twitter and first N products, then save this data to
                output csv file. Wrote in Python 3.6
"""
import csv
import logging
import re
import threading

from json import JSONDecodeError
from queue import Queue
from time import time
from urllib.parse import urlunparse

from Python.basic_functions import initialize_logging

# modules to install, pip3 install requests, bs4
import requests
from bs4 import BeautifulSoup

THREAD_COUNT = 40


class Crawler(threading.Thread):
    """
    Crawler thread class that crawls sub-links["", "about", "about-us", "contact", "contact-us"]
    searching contacts, then collecting title and image source first N products ("collections/all")
    on domain urls.
    """
    __slots__ = ["data", "input_queue", "_urls", "_url_collections", "sess"]

    _email_regex = re.compile("([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4})", re.IGNORECASE)
    _email_black_list = (".png", ".jpg", ".jpeg", ".gif", "example.com")  # ignore this suffix
    _sub_pages = ["", "about", "about-us", "contact", "contact-us"]

    def __init__(self, input_queue, uid):
        """
        :param input_queue: queue with dictionary{"url": "domain.url"} contain domain url
        :type input_queue: Queue
        """
        super().__init__(name=f"Crawler_{uid}")
        self.input_queue = input_queue
        self.sess = requests.Session()
        self.data = None
        self._urls = None
        self._url_collections = None

    def run(self):
        """
        Running until input queue contain any domain to process.
        Iterate the list of sub-pages and request each page, then parse it and
        collect emails, facebook and twitter pages, first N products.
        Append this data to input dict data.
        """
        logging.info("Thread %s running", self.name)

        while not self.input_queue.empty():
            self.data = self.input_queue.get()

            logging.info("Start crawling on domain: %s", self.data["url"])
            self.data["email"] = set()
            self.data["facebook"] = set()
            self.data["twitter"] = set()

            # merge scheme, domain, path to sub-pages
            self._urls = list(map(lambda sub: urlunparse(("http", self.data["url"], sub, None, None, None)),
                                  self._sub_pages))
            # merge scheme, domain, path to collections
            self._url_collections = urlunparse(("http", self.data["url"], "collections/all", None, None, None))

            for url in self._urls:
                logging.debug("Crawling page: %s", url)
                try:
                    response = self.sess.get(url)
                except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError):
                    # ignore pages with errors
                    continue
                if response.status_code == 404:
                    # ignore not found pages
                    continue

                mail, facebook, twitter = self.get_contacts(response.text)
                logging.debug("Found all contacts from sub-page: %s", url)

                self.data["email"].update(mail)
                self.data["facebook"].update(facebook)
                self.data["twitter"].update(twitter)

            self._convert_to_list()
            logging.info("Collected contacts from domain: %s", self.data["url"])
            self.get_first_products()
            logging.info("Collected data from domain: %s", self.data["url"])
            self.sess.close()

        logging.info("Thread %s stopped", self.name)

    def get_contacts(self, data):
        """
        Return all emails, facebook and twitter pages from url

        :param data: data from page
        :return: emails, facebook, twitter
        """
        facebook = set()
        twitter = set()

        logging.debug("Finding emails...")
        # emails are case insensitive (item.lower)
        emails = set([item.lower() for item in self._email_regex.findall(data)
                      if not item.endswith(self._email_black_list)])

        logging.debug("Finding facebook and twitter pages...")
        soup = BeautifulSoup(data, "html.parser")

        for ref in soup.find_all(href=re.compile(r"facebook.com|twitter.com")):
            link = ref.get("href")
            facebook.add(link) if "facebook" in link else twitter.add(link)

        return emails, facebook, twitter

    def get_first_products(self, limit=5):
        """
        Find first N(limit) products from "domain/collections/all" get title and image source
        then append it to input data.

        :param limit: number of first products who want return
        """
        products = []
        logging.info("Finding first %d products from page %s", limit, self._url_collections)

        try:
            response = self.sess.get(self._url_collections)
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError):
            # ignore pages with errors
            self._fill_empty(limit)
            return
        if response.status_code == 404:
            # ignore not found pages
            self._fill_empty(limit)
            return

        soup = BeautifulSoup(response.text, "html.parser")

        for ref in soup.find_all(["a", "href"], href=re.compile(r"/products/")):
            link = ref.get("href")

            if link.startswith("/") and not any([l for l in products if link == l]):  # exact string match
                products.append(link)
            if len(products) >= limit:
                break

        logging.debug("Found first %d products from %s, collecting data...", limit, self._url_collections)
        # merge scheme, domain, path to absolute link, .json
        urls = list(map(lambda path: urlunparse(("http", self.data["url"], path + ".json", None, None, None)),
                        products))

        i = 1
        for url in urls:
            try:
                response = self.sess.get(url)
            except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError):
                # ignore pages with errors
                continue
            if response.status_code == 404:
                # ignore not found pages
                continue

            try:
                data = response.json()
                self.data["title " + str(i)] = data["product"]["title"]
                if data["product"]["image"]:
                    self.data["image " + str(i)] = data["product"]["image"]["src"]
                else:
                    self.data["image " + str(i)] = ""
            except JSONDecodeError:
                self.data["title " + str(i)] = ""
                self.data["image " + str(i)] = ""

            i += 1

        while i <= limit:
            self.data["title " + str(i)] = ""
            self.data["image " + str(i)] = ""
            i += 1

        logging.info("Collected first %s products from page %s", limit, self._url_collections)

    def _fill_empty(self, count):
        """
        Fill empty data.
        """
        for i in range(1, count + 1):
            self.data["title " + str(i)] = ""
            self.data["image " + str(i)] = ""

    def _convert_to_list(self):
        """
        Convert set of data to list or string if contains less than two items
        """
        for item in ["email", "facebook", "twitter"]:
            self.data[item] = list(self.data[item])
            if self.data[item]:
                if len(self.data[item]) == 1:
                    self.data[item] = self.data[item][0]
            else:
                self.data[item] = ""


def load_stores_from_csv(input_file):
    """
    Return dictionary, which loaded from input file.

    :param input_file: input csv file
    :return: dict of urls
    """
    result = []
    logging.info("Starting loading data from file: %s", input_file)

    with open(input_file, encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            result.append({"url": row["url"]})

    logging.info("Loaded data")

    return result


def write_to_csv(data, output_file):
    """
    Write input dictionary(data) into cvs output file

    :param data: data will by write
    :param output_file: output file
    :type data: list
    :type output_file: str
    """
    logging.info("Starting writing data into file: %s", output_file)

    with open(output_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=data[0].keys())
        writer.writeheader()

        for row in data:
            writer.writerow(row)

    logging.info("Wrote data")


def main():
    """
    Main function to load urls, crawl pages and save result in format:
    [url, email, facebook, twitter, title 1, image 1, ..., title n, image n]
    Domain are processing in Threads
    """
    workers = []
    input_queue = Queue()
    start = time()

    initialize_logging(log_file="./shopify_crawler.log", level="info")
    logging.info("Starting...")

    dict_stores = load_stores_from_csv("stores.csv")
    [input_queue.put(i) for i in dict_stores]  # initializing queue (thread-safe)

    # init and start threads
    for uid in range(THREAD_COUNT):
        crawler = Crawler(input_queue, uid)
        workers.append(crawler)
        crawler.start()

    # waiting completion of data collection
    for w in workers:
        w.join()

    write_to_csv(dict_stores, "output.csv")

    end = time()
    logging.info("Elapsed time (seconds) = %s", str(round(end - start, 3)))


if __name__ == "__main__":
    main()
