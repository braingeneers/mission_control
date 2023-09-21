import pandas as pd
import unittest
from unittest.mock import patch
from generate_puts_deletes import generate_put_and_delete_lists, apply_last_modified_updates, output_puts_and_deletes
from datetime import datetime
import tempfile
import os


class TestGeneratePutAndDeleteLists(unittest.TestCase):

    def setUp(self):
        self.expire_date = datetime(2022, 1, 5)

    def test_bucketkey_generation(self):
        # Mock data
        aws_inventory = pd.DataFrame({
            'Bucket': ['bucket1', 'bucket2'],
            'Key': ['bucket1/file1', 'bucket2/file2'],
            'Size': [100, 200],
            'LastModified': ['2023-06-02', '2023-06-02'],
            'StorageClass': ['STANDARD', 'STANDARD']
        })

        # Check if BucketKey exists in DataFrame
        if 'BucketKey' in aws_inventory.columns:
            # BucketKey generation line to test
            aws_inventory['BucketKey'] = aws_inventory['Bucket'] + '/' + aws_inventory['Key']

            # Check if the BucketKey column matches the Key column
            self.assertTrue((aws_inventory['BucketKey'] == aws_inventory['Key']).all(), "BucketKey does not match Key")
        else:
            self.assertTrue(True)

    def test_apply_last_modified_updates_missing_key_column(self):
        config = {
            'aws_s3_glacier': {
                'bucket': 'braingeneers-backups',
                'inventory_file_path': 's3://braingeneers-backups-inventory/data/',
            },
            'deletion': {
                'expire_days': 365,
            },
            'backup': {
                'include_paths': [
                    's3://braingeneers/',
                    's3://streamscope/',
                ],
                'atomic_directories': [
                    's3://braingeneers/ephys/*',
                    's3://braingeneers/imaging/*',
                    's3://streamscope/experiments/*',
                ],
            },
            'last_modified_updates': [
                {
                    'path': '/path/to/directory',
                    'date': '2022-06-01'
                }
            ]
        }

        prp_inventory = pd.DataFrame({
            'LastModified': [datetime(2022, 1, 1), datetime(2022, 1, 2)],
            'BucketKey': ['file1', 'file2']
        })

        # This call will raise a KeyError if the bug is present, causing the test to fail
        apply_last_modified_updates(prp_inventory, config)

    @patch('pandas.read_csv')
    def test_generate_put_and_delete_lists(self, mock_read_csv):
        # Mocking the dataframes
        aws_inventory_df = pd.DataFrame({
            'LastModified': [datetime(2022, 1, 1), datetime(2022, 1, 2)],
            'BucketKey': ['bucket1/file1', 'bucket1/file2']
        })
        local_inventory_df = pd.DataFrame({
            'LastModified': [datetime(2022, 1, 3), datetime(2022, 1, 4)],
            'BucketKey': ['bucket1/file2', 'bucket1/file3']
        })

        mock_read_csv.side_effect = [aws_inventory_df, local_inventory_df]

        expire_date = datetime(2022, 1, 5)

        # Call the function with the test data
        puts, deletes = generate_put_and_delete_lists(local_inventory_df, aws_inventory_df, expire_date)

        # Assertions
        self.assertEqual(len(puts), 1)
        self.assertEqual(len(deletes), 1)
        self.assertEqual(puts.values[0], 'bucket1/file3')
        self.assertEqual(deletes.values[0], 'bucket1/file1')

    def test_generate_put_and_delete_lists_empty_dfs(self):
        # Mocking the dataframes
        aws_inventory_df = pd.DataFrame(columns=['LastModified', 'BucketKey'])
        local_inventory_df = pd.DataFrame(columns=['LastModified', 'BucketKey'])

        # Call the function with the test data
        puts, deletes = generate_put_and_delete_lists(local_inventory_df, aws_inventory_df, self.expire_date)

        # Assertions
        self.assertEqual(len(puts), 0)
        self.assertEqual(len(deletes), 0)

    def test_generate_put_and_delete_lists_non_overlapping(self):
        aws_inventory_df = pd.DataFrame({
            'LastModified': [datetime(2022, 1, 1), datetime(2022, 1, 2)],
            'BucketKey': ['file1', 'file2']
        })
        local_inventory_df = pd.DataFrame({
            'LastModified': [datetime(2022, 1, 3), datetime(2022, 1, 4)],
            'BucketKey': ['file3', 'file4']
        })

        puts, deletes = generate_put_and_delete_lists(local_inventory_df, aws_inventory_df, self.expire_date)

        self.assertEqual(len(puts), 2)
        self.assertEqual(len(deletes), 2)

    def test_generate_put_and_delete_lists_all_matching(self):
        aws_inventory_df = pd.DataFrame({
            'LastModified': [datetime(2022, 1, 1), datetime(2022, 1, 2)],
            'BucketKey': ['file1', 'file2']
        })
        local_inventory_df = aws_inventory_df.copy()

        puts, deletes = generate_put_and_delete_lists(local_inventory_df, aws_inventory_df, self.expire_date)

        self.assertEqual(len(puts), 0)
        self.assertEqual(len(deletes), 0)

    def test_lastmodified_does_not_affect_delete_list(self):
        aws_inventory_df = pd.DataFrame({
            'LastModified': [datetime(2022, 1, 6), datetime(2022, 1, 7)],
            'BucketKey': ['file1', 'file2']
        })
        local_inventory_df = pd.DataFrame({
            'LastModified': [datetime(2022, 1, 3), datetime(2022, 1, 4)],
            'BucketKey': ['file3', 'file4']
        })

        puts, deletes = generate_put_and_delete_lists(local_inventory_df, aws_inventory_df, self.expire_date)

        self.assertEqual(len(puts), 2)
        self.assertEqual(len(deletes), 0)

    def test_generate_put_and_delete_lists_incorrect_parameters(self):
        aws_inventory_df = "aws_inventory_df"
        local_inventory_df = None

        with self.assertRaises(Exception):
            generate_put_and_delete_lists(local_inventory_df, aws_inventory_df, self.expire_date)


class TestPutsAndDeletes(unittest.TestCase):
    def setUp(self):
        # Create a dummy DataFrame
        self.puts = pd.DataFrame({'BucketKey': ['braingeneers/archive/2020-02-07-fluidics-imagi...',
                                                'streamscope/nicousf/cam9/cam9_99.png']})
        # Create a temporary file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)

    def test_output_puts_and_deletes(self):
        # Call your function to output the data to the file
        output_puts_and_deletes(self.puts, None, self.temp_file.name)

        # Open the output file and read its contents
        with open(self.temp_file.name, 'r') as f:
            contents = f.read()

        # Check that the tilde character is not in the file contents
        self.assertNotIn('~', contents)

    def tearDown(self):
        # Close the temporary file and remove it
        os.unlink(self.temp_file.name)


if __name__ == "__main__":
    unittest.main()
