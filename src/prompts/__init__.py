"""
Prompt Engineering Module for InvestIQ
Implements structured prompt templates following best practices.
"""

from .dashboard_prompts import (
    get_dashboard_system_prompt,
    get_dashboard_user_prompt,
    format_context_for_prompt
)

__all__ = [
    'get_dashboard_system_prompt',
    'get_dashboard_user_prompt',
    'format_context_for_prompt'
]

