"""Streamlit Community Cloud entrypoint for Pushan."""

from frontend.cloud_runtime import ensure_cloud_runtime


ensure_cloud_runtime()

# Importing the dashboard renders it after the embedded API is healthy.
from frontend import streamlit_app as _dashboard  # noqa: E402,F401
