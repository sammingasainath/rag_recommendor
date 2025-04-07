#!/usr/bin/env python
"""
Script to set up vector search functionality in Supabase.
This script creates the necessary SQL functions for vector search.

Usage:
    python -m backend.scripts.setup_vector_search
"""

import argparse
import asyncio
import logging
import sys
import os
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("setup_vector_search")

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.config import settings
from backend.services.supabase_service import SupabaseService


async def setup_vector_search(supabase: SupabaseService, sql_path: str):
    """
    Set up vector search functionality by executing SQL script.
    
    Args:
        supabase: Initialized SupabaseService
        sql_path: Path to SQL script
    """
    if not supabase.initialized or not supabase.client:
        logger.error("Supabase service not initialized")
        return False
    
    try:
        # Read SQL script
        with open(sql_path, 'r') as file:
            sql_script = file.read()
        
        logger.info(f"Loaded SQL script from {sql_path}")
        
        # Execute SQL script
        # We need to use Supabase's REST API to execute custom SQL
        result = await execute_sql(supabase, sql_script)
        
        if result:
            logger.info("Vector search setup completed successfully")
            return True
        else:
            logger.error("Vector search setup failed")
            return False
            
    except Exception as e:
        logger.error(f"Error setting up vector search: {e}")
        return False


async def execute_sql(supabase: SupabaseService, sql: str):
    """
    Execute custom SQL in Supabase.
    
    Args:
        supabase: Initialized SupabaseService
        sql: SQL script to execute
        
    Returns:
        True if successful, False otherwise
    """
    # We can use the rpc function to call pg_execute_sql which is a PostgreSQL function 
    # that needs to be available in your Supabase project
    try:
        # Split the SQL script into separate statements if there are multiple
        statements = sql.split(';')
        statements = [stmt.strip() for stmt in statements if stmt.strip()]
        
        for i, stmt in enumerate(statements):
            logger.info(f"Executing SQL statement {i+1}/{len(statements)}")
            
            # Use the REST API to execute the SQL directly
            # This requires service role access
            response = supabase.client.postgrest.rpc(
                "exec_sql", 
                {"sql": stmt}
            ).execute()
            
            if hasattr(response, 'get') and response.get('error'):
                logger.error(f"SQL execution error: {response.get('error')}")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Error executing SQL: {e}")
        return False


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Set up vector search functionality in Supabase")
    parser.add_argument("--sql-path", type=str, help="Path to SQL script", 
                        default=os.path.join(os.path.dirname(__file__), "create_vector_search_function.sql"))
    args = parser.parse_args()
    
    # Check if the SQL file exists
    sql_path = args.sql_path
    if not os.path.exists(sql_path):
        logger.error(f"SQL file not found: {sql_path}")
        return
    
    if settings.USE_MOCK_DATA:
        logger.error("Cannot set up vector search in mock mode - disable USE_MOCK_DATA in settings")
        return
    
    logger.info("Starting vector search setup")
    
    # Initialize Supabase service
    supabase = SupabaseService()
    
    if not supabase.initialized:
        logger.error("Failed to initialize Supabase service")
        return
    
    # Set up vector search
    success = await setup_vector_search(supabase, sql_path)
    
    if success:
        logger.info("Vector search setup completed successfully")
    else:
        logger.error("Vector search setup failed")


if __name__ == "__main__":
    asyncio.run(main()) 