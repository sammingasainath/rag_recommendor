"""
SHL Assessment Catalog Scraping Package
"""

import logging

# Import for easier usage
from .scraper import Scraper
from .utils import GeminiProcessor
from .html_parser import HTMLParser

# Configure root logger
logging.getLogger().setLevel(logging.INFO)

__all__ = ['Scraper', 'GeminiProcessor'] 