"""
Vercel Serverless Function Entry Point for FastAPI
This file re-exports the FastAPI app from the main api module
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import the FastAPI app from the actual location
from src.api.api import app

# Export app at module level for Vercel
# Vercel will detect this as the FastAPI application
__all__ = ["app"]
