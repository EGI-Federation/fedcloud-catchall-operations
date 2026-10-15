"""
Accounting operations

Removes existing records to avoid filling up disk space
This is mostly a substitute for SSM while we decide whether to
actually send the records or not
"""

import glob
import logging
import sys

from dirq.QueueSimple import QueueSimple

from .config import CONF

logger = logging.getLogger(__name__)


def remove_records(site_dir):
    for spool_dir in glob.iglob("*/outgoing/*", root_dir=site_dir):
        logger.debug(f"Cleaning up {spool_dir}")
        dirq = QueueSimple(spool_dir)
        for name in dirq:
            logger.debug(f"Removing element {name}")
            dirq.lock(name)
            dirq.remove(name)
        dirq.purge()


def main():
    CONF(sys.argv[1:])
    logging.basicConfig(level=logging.DEBUG)
    remove_records(CONF.accounting.spool_dir)
