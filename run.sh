#!/bin/bash
export PATH="/Users/shrey/Library/Python/3.9/bin:$PATH"
export PYTHONPATH="$PYTHONPATH:$(pwd)"
echo "Starting Sarvam QA Dashboard..."
streamlit run app.py --server.port 8501 --server.headless true
