"""Tests for the Streamlit Community Cloud bootstrap."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from frontend.cloud_runtime import configure_cloud_environment


class CloudRuntimeTests(unittest.TestCase):
    def test_cloud_environment_uses_writable_runtime_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"PUSHAN_CLOUD_RUNTIME_PATH": directory, "PUSHAN_API_PORT": "8765"},
            clear=True,
        ):
            runtime_root, port = configure_cloud_environment()

            self.assertEqual(runtime_root, Path(directory))
            self.assertEqual(port, 8765)
            self.assertEqual(os.environ["PUSHAN_API_URL"], "http://127.0.0.1:8765")
            self.assertEqual(
                os.environ["PUSHAN_DATABASE_PATH"], str(Path(directory) / "pushan.db")
            )
            self.assertEqual(
                os.environ["PUSHAN_MODEL_PATH"],
                str(Path(directory) / "irrigation_model.joblib"),
            )
            self.assertEqual(
                os.environ["PUSHAN_VECTOR_STORE_PATH"],
                str(Path(directory) / "vector_store"),
            )


if __name__ == "__main__":
    unittest.main()
