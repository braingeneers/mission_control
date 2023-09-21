import argparse
import pandas as pd
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_arguments():
    parser = argparse.ArgumentParser(description='Generate PUT and DELETE lists based on S3 and Glacier inventories.')
    parser.add_argument('--config', type=str, required=True, help='Path to data lifecycle configuration file')
    parser.add_argument('--prp-inventory', type=str, required=True, help='Path to PRP/S3 inventory file')
    parser.add_argument('--aws-inventory', type=str, required=True, help='Path to AWS/Glacier/S3 inventory file')
    parser.add_argument('--puts-output', type=str, default=None, help='Path to output PUTs file')
    parser.add_argument('--deletes-output', type=str, default=None, help='Path to output DELETEs file')
    return parser.parse_args()


def load_config_file(config_path):
    with open(config_path, 'r') as stream:
        try:
            return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)


def load_inventories(prp_inventory_path, aws_inventory_path):
    prp_inventory = pd.read_csv(
        prp_inventory_path,
        names=['LastModified', 'BucketKey'],
        parse_dates=['LastModified'],
    )

    aws_inventory = pd.read_csv(
        aws_inventory_path,
        names=['Bucket', 'BucketKey', 'Size', 'LastModified', 'StorageClass'],
        parse_dates=['LastModified'],
    )

    return prp_inventory, aws_inventory


def apply_last_modified_updates(prp_inventory, config):
    for path in config['backup']['atomic_directories']:
        max_date = prp_inventory[prp_inventory['BucketKey'].str.startswith(path)].LastModified.max()
        prp_inventory.loc[prp_inventory['BucketKey'].str.startswith(path), 'LastModified'] = max_date

    return prp_inventory


def calculate_expire_date(expire_days):
    return datetime.now(timezone.utc) - timedelta(days=expire_days)


def generate_put_and_delete_lists(primary_inventory_df: pd.DataFrame,
                                  glacier_inventory_df: pd.DataFrame,
                                  expire_date):
    # Copy dataframes to not alter the original ones
    local_inventory = primary_inventory_df.copy()
    aws_inventory = glacier_inventory_df.copy()

    puts = local_inventory[~local_inventory.BucketKey.isin(aws_inventory.BucketKey)]
    deletes = aws_inventory[(~aws_inventory.BucketKey.isin(local_inventory.BucketKey)) & (aws_inventory.LastModified < expire_date)]
    return puts['BucketKey'], deletes['BucketKey']


def generate_notification_list(primary_inventory_df: pd.DataFrame,
                               glacier_inventory_df: pd.DataFrame,
                               notification_days,
                               atomic_directories):
    # Copy dataframes to not alter the original ones
    local_inventory = primary_inventory_df.copy()
    aws_inventory = glacier_inventory_df.copy()

    notification_date = calculate_expire_date(notification_days)
    notifications = aws_inventory[(aws_inventory.LastModified < notification_date) & (~aws_inventory.BucketKey.isin(local_inventory.BucketKey))]

    # For atomic directories, retain only one line for all files that match the atomic directory
    for path in atomic_directories:
        notifications.loc[notifications['BucketKey'].str.startswith(path), 'BucketKey'] = path

    return notifications.drop_duplicates()


def output_puts_deletes_and_notifications(puts, deletes, notifications, puts_output_filepath=None, deletes_output_filepath=None, notifications_output_filepath=None):
    if puts_output_filepath is not None:
        puts.to_csv(puts_output_filepath, index=False, header=False, encoding='utf8')
    else:
        print("PUTs:")
        print(puts)

    if deletes_output_filepath is not None:
        deletes.to_csv(deletes_output_filepath, index=False, header=False, encoding='utf8')
    else:
        print("\nDELETEs:")
        print(deletes)

    if notifications_output_filepath is not None:
        notifications.to_csv(notifications_output_filepath, index=False, header=False, encoding='utf8')
    else:
        print("\nNOTIFICATIONS:")
        print(notifications)


def main(config: str, prp_inventory: str, aws_inventory: str, puts_output: str, deletes_output: str):
    config = load_config_file(config)
    df_prp_inventory, df_aws_inventory = load_inventories(prp_inventory, aws_inventory)
    df_prp_inventory = apply_last_modified_updates(df_prp_inventory, config)
    expire_date = calculate_expire_date(config['deletion']['expire_days'])
    puts, deletes = generate_put_and_delete_lists(df_prp_inventory, df_aws_inventory, expire_date)
    notifications = generate_notification_list(df_prp_inventory, df_aws_inventory, config['deletion']['notification_days'], config['backup']['atomic_directories'])
    output_puts_deletes_and_notifications(puts, deletes, notifications, puts_output, deletes_output, "notifications.txt")


if __name__ == "__main__":
    args = parse_arguments()
    main(args.config, args.prp_inventory, args.aws_inventory, args.puts_output, args.deletes_output)
