#!/bin/bash
sudo apt update
sudo apt install -y docker python3 python3-pip
pip install -r backend/requirements.txt
