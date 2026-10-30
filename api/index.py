# -*- coding: utf-8 -*-
# api/index.py
import os
import sys

# Đảm bảo đường dẫn thư mục gốc nằm trong sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app
