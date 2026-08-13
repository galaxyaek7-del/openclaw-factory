import sys
from pathlib import Path
_FACTORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_FACTORY_ROOT))

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import requests

from channels.gumroad_publisher import _gumroad_error, _PART_SIZE


def _resp(success=True, **extra):
    body = {"success": success}
    body.update(extra)
    return MagicMock(status_code=200, headers={}, json=lambda: body)


def _tmp_file(suffix=".pdf", data=b"test"):
    """Create a temp file (never in the repo root) and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return path


class TestGumroadApiFix(unittest.TestCase):

    @patch('requests.post')
    @patch('channels.gumroad_publisher._request_with_retry')
    def test_create_product_full_flow(self, mock_request, mock_post):
        # 1. presign -> 2. S3 part PUT -> 3. create product. Complete is a
        # direct requests.post (never retried), not _request_with_retry.
        presign = _resp(upload_id="u123", key="k123",
                        file_url="https://s3/gumroad/attachments/file.pdf",
                        parts=[{"part_number": 1, "presigned_url": "https://s3.upload/part1"}])
        put_resp = _resp()
        put_resp.headers = {"ETag": '"etag-abc"'}
        create = _resp(product={"id": "p123", "short_url": "https://gum.co/p123"})
        mock_request.side_effect = [presign, put_resp, create]
        mock_post.side_effect = [
            _resp(file_url="https://s3/gumroad/attachments/file.pdf"),  # complete
            create,  # create product
        ]

        from channels.gumroad_publisher import create_product

        pdf = _tmp_file()
        try:
            product = create_product("token", {"file_path": pdf, "price_cents": 1000, "title": "Test Product"})
        finally:
            os.unlink(pdf)

        self.assertEqual(product["id"], "p123")
        self.assertEqual(mock_request.call_count, 2)  # presign + S3 PUT

        # The S3 part PUT must have carried the file bytes.
        put_call = mock_request.call_args_list[1]
        self.assertEqual(put_call[0][0], "PUT")
        self.assertEqual(put_call[0][1], "https://s3.upload/part1")

        # Complete must carry upload_id, key AND the parts[][part_number] +
        # parts[][etag] pairs Gumroad's /v2/files/complete requires.
        self.assertEqual(mock_post.call_count, 2)  # complete + create
        complete_url = mock_post.call_args_list[0][0][0]
        self.assertEqual(complete_url, "https://api.gumroad.com/v2/files/complete")
        complete_data = mock_post.call_args_list[0].kwargs.get("data") or mock_post.call_args_list[0][0][1]
        complete_list = list(complete_data)
        self.assertIn(("upload_id", "u123"), complete_list)
        self.assertIn(("key", "k123"), complete_list)
        self.assertIn(("parts[][part_number]", 1), complete_list)
        self.assertIn(('parts[][etag]', '"etag-abc"'), complete_list)

    @patch('channels.gumroad_publisher._abort_upload')
    @patch('requests.post')
    @patch('channels.gumroad_publisher._request_with_retry')
    def test_multipart_upload_captures_all_etags(self, mock_request, mock_post, mock_abort):
        presign = _resp(upload_id="u1", key="k1",
                        parts=[
                            {"part_number": 1, "presigned_url": "https://s3/part1"},
                            {"part_number": 2, "presigned_url": "https://s3/part2"},
                        ])
        p1 = _resp(); p1.headers = {"ETag": '"etag-1"'}
        p2 = _resp(); p2.headers = {"ETag": '"etag-2"'}
        create = _resp(product={"id": "p9"})
        mock_request.side_effect = [presign, p1, p2, create]
        mock_post.side_effect = [
            _resp(file_url="https://s3/file"),  # complete
            create,  # create product
        ]

        from channels.gumroad_publisher import create_product

        big = _tmp_file(suffix=".bin", data=b"x" * (_PART_SIZE + 1))
        try:
            create_product("token", {"file_path": big, "price_cents": 500, "title": "Multi"})
        finally:
            os.unlink(big)

        complete_data = mock_post.call_args_list[0].kwargs.get("data") or mock_post.call_args_list[0][0][1]
        complete_list = list(complete_data)
        # access_token, upload_id, key, then two part_number/etag pairs.
        self.assertEqual(complete_list[0], ("access_token", "token"))
        self.assertEqual(complete_list[3], ("parts[][part_number]", 1))
        self.assertEqual(complete_list[4], ('parts[][etag]', '"etag-1"'))
        self.assertEqual(complete_list[5], ("parts[][part_number]", 2))
        self.assertEqual(complete_list[6], ('parts[][etag]', '"etag-2"'))
        mock_abort.assert_not_called()

    @patch('channels.gumroad_publisher._abort_upload')
    @patch('requests.post')
    @patch('channels.gumroad_publisher._request_with_retry')
    def test_presign_failure_no_complete(self, mock_request, mock_post, mock_abort):
        mock_request.return_value = _resp(upload_id="u123", parts=[])

        from channels.gumroad_publisher import create_product

        pdf = _tmp_file()
        try:
            with self.assertRaises(RuntimeError):
                create_product("token", {"file_path": pdf, "price_cents": 1000, "title": "Test"})
        finally:
            os.unlink(pdf)

        for call in mock_request.call_args_list:
            self.assertNotEqual(call[0][1], "https://api.gumroad.com/v2/files/complete")
        mock_post.assert_not_called()
        mock_abort.assert_not_called()

    @patch('channels.gumroad_publisher._abort_upload')
    @patch('requests.post')
    @patch('channels.gumroad_publisher._request_with_retry')
    def test_s3_put_without_etag_aborts_and_raises(self, mock_request, mock_post, mock_abort):
        presign = _resp(upload_id="u1", key="k1",
                        parts=[{"part_number": 1, "presigned_url": "https://s3/part1"}])
        no_etag = _resp()
        no_etag.headers = {}
        mock_request.side_effect = [presign, no_etag]
        mock_post.return_value = _resp(file_url="https://s3/file")

        from channels.gumroad_publisher import create_product

        pdf = _tmp_file()
        try:
            with self.assertRaises(RuntimeError) as ctx:
                create_product("token", {"file_path": pdf, "price_cents": 1000, "title": "Test"})
            self.assertIn("no ETag", str(ctx.exception))
        finally:
            os.unlink(pdf)
        mock_abort.assert_called_once_with("token", "u1")
        mock_post.assert_not_called()

    @patch('channels.gumroad_publisher._abort_upload')
    @patch('requests.post')
    @patch('channels.gumroad_publisher._request_with_retry')
    def test_complete_failure_aborts_and_reports_error_field(self, mock_request, mock_post, mock_abort):
        presign = _resp(upload_id="u1", key="k1",
                        parts=[{"part_number": 1, "presigned_url": "https://s3/part1"}])
        p1 = _resp(); p1.headers = {"ETag": '"etag-1"'}
        mock_request.side_effect = [presign, p1]
        mock_post.return_value = _resp(success=False, error="The upload_id does not exist")

        from channels.gumroad_publisher import create_product

        pdf = _tmp_file()
        try:
            with self.assertRaises(RuntimeError) as ctx:
                create_product("token", {"file_path": pdf, "price_cents": 1000, "title": "Test"})
            self.assertIn("The upload_id does not exist", str(ctx.exception))
            self.assertNotIn("None", str(ctx.exception))
        finally:
            os.unlink(pdf)
        mock_abort.assert_called_once_with("token", "u1")

    def test_gumroad_error_prefers_error_field(self):
        self.assertEqual(_gumroad_error({"error": "boom", "message": "legacy"}), "boom")
        self.assertEqual(_gumroad_error({"message": "legacy only"}), "legacy only")
        self.assertEqual(_gumroad_error({}), "unknown error")
        self.assertEqual(_gumroad_error("raw text"), "raw text")


if __name__ == '__main__':
    unittest.main()
