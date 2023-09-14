#!/usr/bin/env python3
"""
A service that looks at individual logs of MQTT messages written to 
an s3 bucket and concatenates all of those log files together periodically.
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
    assert uri.startswith('s3://braingeneers/')
    s3_client.delete_object(Bucket='braingeneers', Key=uri[len('s3://braingeneers/'):])


def combine_logs(singletons: str, combined: str):
    """
    All files with the s3 path:
      s3://braingeneers/logs/{uuid}/{time_stamp}.{singletons}.csv
    will be combined into one file:
      s3://braingeneers/logs/{uuid}/{start_time_stamp}.{combined}.csv
    Then the singletons will be deleted.
    """
    print(f'Combining logs at {combined} minute interval...')
    logs = defaultdict(list)
    files_to_delete = list()
    # single-line log path format is: s3://braingeneers/logs/{uuid}/{current_time}.1.csv
    for log in s3wrangler.list_objects(path='s3://braingeneers/logs/', suffix=[f'.{singletons}.csv']):
        log_uuid = log[len("s3://braingeneers/logs/"):].split("/")[0]
        with smart_open.open(log, 'r') as r:
            logs[log_uuid].append(r.read())
        files_to_delete.append(log)

    for log_uuid, log_entries in logs.items():
        log_entries.sort()
        start_time_stamp = log_entries[0].split(",")[0]
        with smart_open.open(f's3://braingeneers/logs/{log_uuid}/{start_time_stamp}.{combined}.csv', 'w') as w:
            w.write(''.join(log_entries))  # log entries are expected to all end in newlines

        print(f'{combined}: {log_uuid} combined {len(log_entries)} files.')

    # assuming everything went alright, we can now clean up the old files
    for uri in files_to_delete:
        delete_s3_object(uri)
    print(f'{len(files_to_delete)} deleted.  Example: {files_to_delete[0]}')


def main():
    """
    An infinite loop that combines the csv-formatted log files we generate in s3.

    Log files ending in ".1.csv" are expected to contain one csv-formatted line.

    These are combined every 5 minutes into a file ending in ".5m.csv"...
    which are in turn combined every 24 hours into files ending in ".24h.csv".
    """
    print('Now starting up the log aggregator...')
    seconds_per_day = 24 * 60 * 60  # seconds per day
    while True:
        # iterate the loop every five minutes for 24 hours, then reset
        for five_minute_interval in range(0, seconds_per_day + 300, 300):
            # combine all single-line logs into a 5 minute log
            combine_logs(singletons='1', combined='5m')

            # combine all 5 minute logs into a 24 hour log at the top of the morning each day
            if five_minute_interval == 0:
                combine_logs(singletons='5m', combined='24h')
            print('Sleeping for 5 minutes...')
            time.sleep(300)  # 5 minutes


if __name__ == '__main__':
    main()
