#!/usr/bin/env python3
"""
A service that subscribes to the "telemetry/#" topic and writes all received messages into a central s3 bucket.

Each log message is written as its own .csv file.  A separate service is intended to run as a cron job and
concatenate all logs files together periodically.
"""
import functools
import time

from collections import defaultdict
from typing import Optional, List, Set

import braingeneers.utils.smart_open_braingeneers as smart_open
from braingeneers.utils.common_utils import _lazy_init_s3_client
from braingeneers.utils import s3wrangler


s3_client = _lazy_init_s3_client()


# TODO: Move to braingeneers utils
def retry(intervals: Optional[List] = None, errors: Optional[Set] = None):
    """Retry decorator."""
    if intervals is None:
        intervals = [1, 1, 2, 4]

    def decorate(func):
        @functools.wraps(func)
        def call(*args, **kwargs):
            while True:
                try:
                    return func(*args, **kwargs)
                except tuple(errors) as e:
                    if not intervals:
                        raise
                    interval = intervals.pop(0)
                    print(f"Error in {func}: {e}. Retrying after {interval} s...")
                    time.sleep(interval)
        return call
    return decorate


@retry(errors={Exception})
def delete_s3_object(uri: str):
    s3_client.delete_object(Bucket='braingeneers', Key=uri[len('s3://braingeneers/'):])


def batch_1000_logs(singletons):
    """
    Generates a list of 1000 logs each time, or an empty list
    if there are not enough logs to make a batch of 1000.
    """
    logs = []
    for log in s3wrangler.list_objects(path='s3://braingeneers/logs/', suffix=[f'.{singletons}.csv']):
        logs.append(log)
        if len(logs) % 1000 == 0:
            yield logs  # return next batch of 1000
            logs = []  # reset
    return []


def combine_logs(singletons: str, combined: str):
    """
    All files with the s3 path:
      s3://braingeneers/logs/{uuid}/{time_stamp}.{singletons}.csv
    will be combined into one file:
      s3://braingeneers/logs/{uuid}/{start_time_stamp}.{combined}.csv
    Then the singletons will be deleted.
    """

    # single-line log path format is: s3://braingeneers/logs/{uuid}/{current_time}.1.csv
    for batch in batch_1000_logs(singletons):  # returns lists of 1000 logs, or an empty list
        print(f'Combining 1000 logs...')
        logs = defaultdict(list)
        for log in batch:
            log_uuid = log[len("s3://braingeneers/logs/"):].split("/")[0]
            with smart_open.open(log, 'r') as r:
                logs[log_uuid].append(r.read())

        for log_uuid, log_entries in logs.items():
            log_entries.sort()
            start_time_stamp = log_entries[0].split(",")[0]
            with smart_open.open(f's3://braingeneers/logs/{log_uuid}/{start_time_stamp}.{combined}.csv', 'w') as w:
                w.write(''.join(log_entries))  # log entries are expected to all end in newlines

            print(f'{combined}: {log_uuid} combined {len(log_entries)} files.')

        # assuming everything went alright, we can now clean up the old files
        for uri in batch:
            delete_s3_object(uri)
        print(f'1000 files deleted.  Example: {batch[0]}')


def main():
    """
    An infinite loop that combines the csv-formatted log files we generate in s3.

    Log files ending in ".1.csv" are expected to contain one csv-formatted line.

    These are combined into a file ending in ".1k.csv" for every 1000 files.
    which are in turn combined into files ending in ".1m.csv" for every 1,000,000 files.
    """
    print('Now starting up the log aggregator...')
    while True:
        combine_logs(singletons='1', combined='1k')
        combine_logs(singletons='1k', combined='1m')
        time.sleep(120)  # check to combine every 2 minutes


if __name__ == '__main__':
    main()
