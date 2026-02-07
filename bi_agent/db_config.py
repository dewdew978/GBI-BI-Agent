"""
Database configuration and connection management for SQL Server.

This module provides utilities for connecting to Microsoft SQL Server
and retrieving schema information for the LLM context.
"""

import urllib.parse
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine


def create_db_engine(server: str, database: str, username: str, password: str, driver: str = "ODBC Driver 18 for SQL Server") -> Engine:
    """
    Create a SQLAlchemy engine for MS SQL Server connection.

    Args:
        server: SQL Server hostname
        database: Database name
        username: Database username
        password: Database password
        driver: ODBC driver name (default: ODBC Driver 18 for SQL Server)

    Returns:
        SQLAlchemy Engine object
    """
    # Build ODBC connection string (not URL-encoded yet)
    odbc_string = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
    )

    # URL-encode the entire ODBC connection string
    params = urllib.parse.quote_plus(odbc_string)

    # Build SQLAlchemy connection URL
    connection_string = f"mssql+pyodbc:///?odbc_connect={params}"

    # Create engine
    engine = create_engine(connection_string, echo=False)

    return engine


def validate_connection(engine: Engine) -> tuple[bool, str]:
    """
    Validate database connection.

    Args:
        engine: SQLAlchemy Engine object

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT @@VERSION AS version"))
            version = result.scalar()
            return True, f"Connected successfully. SQL Server version: {version[:50]}..."
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def get_schema_info(engine: Engine, limit_tables: list[str] = None, max_tables: int = 20) -> str:
    """
    Retrieve database schema information formatted for LLM context.

    Args:
        engine: SQLAlchemy Engine object
        limit_tables: Optional list of table names to include (None = all tables)
        max_tables: Maximum number of tables to include (default: 20)

    Returns:
        Formatted string containing schema information
    """
    try:
        with engine.connect() as connection:
            # Query to get table and column information
            query = text("""
                SELECT
                    t.TABLE_SCHEMA,
                    t.TABLE_NAME,
                    c.COLUMN_NAME,
                    c.DATA_TYPE,
                    c.IS_NULLABLE,
                    c.COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.TABLES t
                INNER JOIN INFORMATION_SCHEMA.COLUMNS c
                    ON t.TABLE_SCHEMA = c.TABLE_SCHEMA
                    AND t.TABLE_NAME = c.TABLE_NAME
                WHERE t.TABLE_TYPE = 'BASE TABLE'
                ORDER BY t.TABLE_SCHEMA, t.TABLE_NAME, c.ORDINAL_POSITION
            """)

            result = connection.execute(query)
            rows = result.fetchall()

            # Organize data by table
            tables = {}
            for row in rows:
                schema_name = row[0]
                table_name = row[1]
                full_table_name = f"{schema_name}.{table_name}"

                # Skip if not in limit_tables (if specified)
                if limit_tables and full_table_name not in limit_tables:
                    continue

                if full_table_name not in tables:
                    tables[full_table_name] = []

                column_info = {
                    'name': row[2],
                    'type': row[3],
                    'nullable': row[4],
                    'default': row[5]
                }
                tables[full_table_name].append(column_info)

            # Limit number of tables if needed
            table_names = list(tables.keys())[:max_tables]

            # Format as readable text
            schema_text = "Database Schema:\n\n"

            for table_name in table_names:
                schema_text += f"Table: {table_name}\n"
                schema_text += "Columns:\n"

                for col in tables[table_name]:
                    nullable = "NULL" if col['nullable'] == 'YES' else "NOT NULL"
                    schema_text += f"  - {col['name']} ({col['type']}, {nullable})\n"

                schema_text += "\n"

            if len(tables) > max_tables:
                schema_text += f"\n... and {len(tables) - max_tables} more tables\n"

            return schema_text

    except Exception as e:
        return f"Error retrieving schema: {str(e)}"
