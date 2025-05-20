#!/bin/bash

# Navigate to the project directory
cd /home/ubuntu/customer_service_mcp

# # Create virtual environment if it doesn't exist
# if [ ! -d "venv" ]; then
#     python3 -m venv venv
# fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
# pip install -r requirements.txt

# Start the client application
python3 main.py

# Deactivate virtual environment when done
deactivate
