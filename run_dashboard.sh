#!/bin/bash
# 啟動 Streamlit Dashboard

cd "$(dirname "$0")"
uv run streamlit run streamlit_app.py
