"""
Business Intelligence Agent Package

This package contains the agent definitions, tools, and database utilities
for the BI agent pipeline using Google ADK.
"""

from bi_agent.agent import (
    # Root agent (main entry point for ADK web)
    root_agent,
    root_runner,
    # Individual agents
    text_to_sql_agent,
    text_to_sql_runner,
    sql_executor_agent,
    data_formatter_agent,
    visualization_agent,
    explanation_agent,
    # Pipelines
    insight_pipeline,
    insight_runner,
    # Constants
    GEMINI_MODEL
)

from bi_agent.bi_service import BIService
from bi_agent.tools import DatabaseTools, execute_sql_and_format, get_database_schema

__all__ = [
    # Root agent (required for ADK web)
    'root_agent',
    'root_runner',
    # Individual agents
    'text_to_sql_agent',
    'text_to_sql_runner',
    'sql_executor_agent',
    'data_formatter_agent',
    'visualization_agent',
    'explanation_agent',
    # Pipelines
    'insight_pipeline',
    'insight_runner',
    # Constants
    'GEMINI_MODEL',
    # Services and Tools
    'BIService',
    'DatabaseTools',
    'execute_sql_and_format',
    'get_database_schema',
]
