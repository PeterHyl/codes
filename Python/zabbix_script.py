"""
:Module: zabbix_script.py

:Authors:
    Peter Hyl

:Description: This module contains the discovery and check for every item.
              Script is for Linux
"""
import argparse
import json
import logging
import os
import sys

from fcntl import LOCK_EX, LOCK_UN, flock
from Python.basic_functions import initialize_logging

ITEMS_DIR = "path_to_items"


def check_item(item):
    """
    Check item status
    """
    name = '/tmp/zabbix/items.tmp'
    file = open(name, 'r')
    flock(file, LOCK_EX)
    try:
        logging.info('Read from file')
        data = file.read()
    finally:
        flock(file, LOCK_UN)
        file.close()
    logging.info('Load data from json')
    result = json.loads(data)
    try:
        print(result[item])
        logging.info('Print result')
    except Exception as exp:
        logging.error(exp)


def discovery():
    """
    Discovery items
    """
    result = []
    items = [d for d in os.listdir(ITEMS_DIR) if os.path.isdir(os.path.join(ITEMS_DIR, d))]

    for item in items:
        result.append({'{#ITEM}': item})
    print(json.dumps({'data': result}))
    logging.info('Print result')


def main(args):
    if args.check:
        check_item(args.check[0])
    elif args.discovery:
        discovery()


def parse_arguments():
    """
    Method parses command line arguments

    Returns:
        environment with command line arguments
    """

    parser = argparse.ArgumentParser(
        description="Check state for zabbix")

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("-c", "--check", action='store', nargs=1, type=str, metavar='item',
                       help=r"Return state")
    group.add_argument("-d", "--discovery", action="store_true", required=False,
                       help=r"Discover all items")
    logging.info("Command %s", sys.argv)

    return parser.parse_args()


if __name__ == "__main__":
    initialize_logging(log_file="/var/log/zabbix.log", level="debug")
    main(parse_arguments())
