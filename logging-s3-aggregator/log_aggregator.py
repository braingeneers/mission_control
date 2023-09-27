#!/usr/bin/env python3
"""
A service that looks at individual logs of MQTT messages written to 
an s3 bucket and concatenates all of those log files together periodically.
"""
import os.path
import time
import traceback
import shutil
import sys

from tenacity import retry, wait_exponential, stop_after_attempt
from collections import defaultdict

import braingeneers.utils.smart_open_braingeneers as smart_open
from braingeneers.utils.common_utils import _lazy_init_s3_client
from braingeneers.utils import s3wrangler


s3_client = _lazy_init_s3_client()


def log_to_stderr(retry_state):
    """Print our retries to the screen so that we know what's going on."""
    print(f"Retrying: {retry_state.attempt_number}...", file=sys.stderr)


# retry @ [0s, 1s, 2s, 4s, 8s] before raising
@retry(wait=wait_exponential(multiplier=1, min=1, max=8), stop=stop_after_attempt(5), after=log_to_stderr)
def delete_s3_object(uri: str):
    assert uri.startswith('s3://braingeneers/logs/'), uri
    print(f'Now deleting: {uri}')
    s3_client.delete_object(Bucket='braingeneers', Key=uri[len('s3://braingeneers/'):])


def batch_100_logs(singletons: str):
    """
    Generates a list of 100 logs specific to a UUID each time as well as the UUID...
    or an empty list and empty string if there are not enough logs to make a batch of 100.
    """
    logs = defaultdict(list)
    for log in s3wrangler.list_objects(path='s3://braingeneers/logs/', suffix=[f'.{singletons}.tsv']):
        log_name = log[len("s3://braingeneers/logs/"):].rsplit("/", 1)[0]
        logs[log_name].append(log)
        if len(logs[log_name]) % 100 == 0:
            yield log_name, logs[log_name]  # return next batch of 100
            logs[log_name] = []  # reset
    return '', []  # we're out of logs to return


def format_log_entries(log_entries: dict, header_keys: list):
    """
    Given a dict of log entries, return a string to write to a new log file.

    For example, the inputs:
        log_entries=
            {'2023-09-21_23-24-59': {'TOPIC': 'telemetry/0000-00-00-efi-testing/log/zambezi-cam/cmnd',
                                     '': 'ॐ'},
             '2023-09-21_23-25-00': {'TOPIC': 'telemetry/0000-00-00-efi-testing/log/zambezi-cam/cmnd',
                                     '': 'ॐ'}
            }
        header_keys=
            ['TIMESTAMP', 'TOPIC', '']

    Will return the following as a formatted string:
        TIMESTAMP	TOPIC
        2023-09-21_23-24-59	telemetry/0000-00-00-efi-testing/log/zambezi-cam/cmnd	ॐ
        2023-09-21_23-25-00	telemetry/0000-00-00-efi-testing/log/zambezi-cam/cmnd	ॐ
    """
    header_keys = sorted(set(header_keys))
    header_keys.remove('_LOGTIMESTAMP')
    header_keys.remove('_LOGTOPIC')
    formatted_lines = '\t'.join(['_LOGTIMESTAMP', '_LOGTOPIC'] + header_keys) + '\n'  # start with the first line (the header)
    timestamps = sorted(log_entries.keys())
    for timestamp in timestamps:
        entry = log_entries[timestamp]
        formatted_lines += '\t'.join([timestamp] + [entry['_LOGTOPIC']] + [str(entry.get(k, '')) for k in header_keys]) + '\n'
    return formatted_lines, timestamps[0]


def combine_logs(singletons: str, combined: str):
    """
    All files with the s3 path:
      s3://braingeneers/logs/{uuid}/{time_stamp}.{singletons}.tsv
    will be combined into one file:
      s3://braingeneers/logs/{uuid}/{start_time_stamp}.{combined}.tsv
    Then the singletons will be deleted.
    """
    for log_uuid, batch in batch_100_logs(singletons):  # batch is a list of 100 logs, or empty list
        print(f'Reading {len(batch)} {log_uuid} logs...')
        logs = dict()
        all_header_keys = list()
        header_keys = list()
        for log in batch:
            print(f'Reading log: {log}')
            with smart_open.open(log, 'r') as r:
                for line in r:
                    if line.startswith('_LOGTIMESTAMP'):  # header line
                        header_keys = [j.strip() for j in line.split('\t')]
                        all_header_keys += header_keys
                    else:
                        row = [j.strip() for j in line.split('\t')]
                        assert len(header_keys) == len(row), f'File header conflicts with tab entries: {log}\n' \
                                                             f'keys: {header_keys}\nrow: {row}\n'
                        messages = dict()
                        for i in range(1, len(row)):
                            messages[header_keys[i]] = row[i]
                        logs[row[0]] = messages

        log_entries, start_time = format_log_entries(logs, all_header_keys)
        print(log_entries)
        combined_file = f's3://braingeneers/logs/{log_uuid}/{start_time}.{combined}.tsv'
        print(f'Writing {len(batch)} logs to: {combined_file}')
        with smart_open.open(combined_file, 'w') as w:
            w.write(log_entries)  # log entries are expected to all end in newlines
        print(f'{combined}: {log_uuid} combined {len(batch)} files.')

        # assuming everything went alright, we can now clean up the old files
        print(f'Deleting {len(batch)} files.')
        for uri in batch:
            delete_s3_object(uri)
        print(f'Successfully deleted {len(batch)} files.')


def main():
    """
    An infinite loop that combines the tsv-formatted log files we generate in s3.

    All log files have a tsv-formatted header line at the top of the file.

    Log files ending in ".1.tsv" are expected to contain one tsv-formatted log line.
    Log files ending in ".100.tsv" are expected to contain one hundred tsv-formatted log lines.
    Log files ending in ".10k.tsv" are expected to contain ten thousand tsv-formatted log lines.
    Log files ending in ".1m.tsv" are expected to contain one million tsv-formatted log lines.
    """
    print('Checking and moving credentials files...')
    src = '/secrets/prp-s3-credentials/credentials'
    dsts = ['/root/.aws/credentials', os.path.expanduser('~/.aws/credentials')]
    for dst in dsts:
        if not os.path.exists(dst):
            if not os.path.exists(src):
                raise RuntimeError(f'{src} does not exist!  Are your secrets mounted?')
            os.makedirs(dst[:-len('/credentials')], exist_ok=True)
            shutil.copyfile(src, dst)

    print('Now starting up the log aggregator...')
    while True:
        try:
            combine_logs(singletons='1', combined='100')
            combine_logs(singletons='100', combined='10k')
            combine_logs(singletons='10k', combined='1m')
        except Exception as e:  # this is a long-lived logging service; never say die
            print(f'ERROR: {e}\n{traceback.format_exc()}', file=sys.stderr)
        time.sleep(120)  # check to combine every 2 minutes


if __name__ == '__main__':
    main()
