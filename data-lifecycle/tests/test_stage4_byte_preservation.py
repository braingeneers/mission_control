"""Exercise the real smart_open compression layer with in-memory S3 transport."""

import builtins
import gzip
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from stage4_process_puts_deletes import stream_upload


class TestBackupBytes(unittest.TestCase):
    def test_stream_preserves_stored_bytes_without_compression_codecs(self):
        plain = b'hello world'
        # A valid single-segment Zstandard frame containing one raw block.
        zstd = bytes.fromhex('28b52ffd200b590000') + plain
        gzip_bytes = gzip.compress(plain * 100, mtime=123)
        cases = [
            ('object.bin', 'object.bin', plain),
            ('object.zst', 'object.zst', zstd),
            ('object.npz.zst', 'object.npz.zst', zstd),
            ('object.gz', 'object.gz', gzip_bytes),
            ('object.gz', 'object.bin', gzip_bytes),
            ('object.bin', 'object.gz', plain),
            ('object.bin', 'object.zst', plain),
        ]
        real_import = builtins.__import__

        def no_optional_codec(name, *args, **kwargs):
            if name.split('.')[0] in {'backports', 'zstandard', 'compression'}:
                raise ModuleNotFoundError('Optional compression codecs are unavailable')
            return real_import(name, *args, **kwargs)

        for source_name, destination_name, payload in cases:
            with self.subTest(source=source_name, destination=destination_name):
                source_client, destination_client = object(), object()
                captured = []
                progress = []

                class Destination(io.BytesIO):
                    def close(self):
                        if not self.closed:
                            captured.append(self.getvalue())
                        super().close()

                def s3_transport(uri, mode, transport_params):
                    if mode == 'rb':
                        self.assertEqual(uri, f's3://source/{source_name}')
                        self.assertIs(transport_params['client'], source_client)
                        return io.BytesIO(payload)
                    self.assertEqual(mode, 'wb')
                    self.assertEqual(uri, f's3://backup/source/{destination_name}')
                    self.assertIs(transport_params['client'], destination_client)
                    self.assertTrue(transport_params['multipart_upload'])
                    self.assertEqual(transport_params['min_part_size'], 64 * 1024 * 1024)
                    return Destination()

                with patch('smart_open.s3.open_uri', side_effect=s3_transport), patch(
                    'stage4_process_puts_deletes.get_source_s3_client', return_value=source_client,
                ), patch('builtins.__import__', side_effect=no_optional_codec):
                    copied = stream_upload(
                        f's3://source/{source_name}',
                        f's3://backup/source/{destination_name}',
                        s3_client=destination_client,
                        copy_chunk_bytes=7,
                        progress_callback=progress.append,
                    )
                self.assertEqual(captured, [payload])
                self.assertEqual(copied, len(payload))
                self.assertEqual(sum(progress), len(payload))
                self.assertTrue(all(0 < size <= 7 for size in progress))


if __name__ == '__main__':
    unittest.main()
