#!/usr/bin/env python
"""
Master script to set up the full real implementation for the assessment recommendation system.
This script handles:
1. Setting up vector search functionality in Supabase
2. Generating embeddings for all assessments in the database
3. Testing the API endpoints

Usage:
    python -m backend.scripts.setup_real_implementation

Options:
    --skip-vector-setup   Skip the vector search setup step
    --skip-embeddings     Skip the embeddings generation step
    --skip-api-test       Skip the API testing step
    --batch-size INT      Number of assessments to process in each batch [default: 25]
    --force-embeddings    Force regeneration of embeddings for all assessments
    --dry-run             Don't actually update the database, just print what would be done
"""

import argparse
import asyncio
import logging
import sys
import os
import time
import json
import importlib.util
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("setup_real_implementation")

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# First, ensure environment settings
from backend.core.config import settings
settings.USE_MOCK_DATA = False

# Import services and scripts
from backend.services.supabase_service import SupabaseService
from backend.services.gemini_service import gemini_service


async def setup_vector_search():
    """Set up vector search functionality in Supabase."""
    logger.info("--- Setting up vector search functionality ---")
    
    # Import the setup script
    try:
        import backend.scripts.setup_vector_search as setup_vector_search
        
        # Create a new SupabaseService instance
        supabase = SupabaseService()
        
        if not supabase.initialized:
            logger.error("Failed to initialize Supabase service")
            return False
        
        # Path to the SQL script
        sql_path = os.path.join(os.path.dirname(__file__), "create_vector_search_function.sql")
        
        if not os.path.exists(sql_path):
            logger.error(f"SQL file not found: {sql_path}")
            return False
        
        # Set up vector search
        success = await setup_vector_search.setup_vector_search(supabase, sql_path)
        
        if success:
            logger.info("Vector search setup completed successfully")
            return True
        else:
            logger.error("Vector search setup failed")
            return False
            
    except Exception as e:
        logger.error(f"Error setting up vector search: {e}")
        return False


async def generate_embeddings(args):
    """Generate embeddings for all assessments in the database."""
    logger.info("--- Generating embeddings for assessments ---")
    
    # Import the generate_embeddings script
    try:
        # Run as a separate process to ensure clean environment
        import subprocess
        
        cmd = [
            sys.executable, 
            "-m", 
            "backend.scripts.generate_embeddings",
            "--batch-size", 
            str(args.batch_size)
        ]
        
        if args.force_embeddings:
            cmd.append("--force")
            
        if args.dry_run:
            cmd.append("--dry-run")
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        # Run the process
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Stream output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logger.info(output.strip())
        
        # Get return code
        return_code = process.poll()
        
        # Get any remaining output
        stdout, stderr = process.communicate()
        if stdout:
            logger.info(stdout)
        if stderr:
            logger.error(stderr)
        
        if return_code == 0:
            logger.info("Embedding generation completed successfully")
            return True
        else:
            logger.error(f"Embedding generation failed with return code {return_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        return False


async def test_api_endpoints():
    """Test the API endpoints to ensure everything is working."""
    logger.info("--- Testing API endpoints ---")
    
    # Check if httpx is installed
    if importlib.util.find_spec("httpx") is None:
        logger.error("httpx library not found, cannot test API endpoints")
        return False
    
    import httpx
    base_url = "http://localhost:8000/api"
    
    # Test the health endpoint
    try:
        logger.info("Testing health endpoint...")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")
            
            if response.status_code == 200:
                logger.info(f"Health check successful: {response.json()}")
            else:
                logger.error(f"Health check failed: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error testing health endpoint: {e}")
        return False
    
    # Test the assessments endpoint
    try:
        logger.info("Testing assessments endpoint...")
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/assessments")
            
            if response.status_code == 200:
                assessments = response.json()
                logger.info(f"Retrieved {len(assessments)} assessments")
            else:
                logger.error(f"Assessments retrieval failed: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error testing assessments endpoint: {e}")
        return False
    
    # Test the recommendations endpoint
    try:
        logger.info("Testing recommendations endpoint...")
        
        test_query = "I need assessments for a software developer position that test coding skills and problem solving"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/recommendations", 
                json={"query": test_query},
                params={"top_k": 3}
            )
            
            if response.status_code == 200:
                result = response.json()
                recommendations = result.get("recommendations", [])
                logger.info(f"Retrieved {len(recommendations)} recommendations")
                logger.info(f"Processing time: {result.get('processing_time', 0):.2f}s")
                
                # Print the recommendations
                for i, rec in enumerate(recommendations):
                    logger.info(f"Recommendation {i+1}: {rec.get('name')} (similarity: {rec.get('similarity'):.2f})")
            else:
                logger.error(f"Recommendations retrieval failed: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Error testing recommendations endpoint: {e}")
        return False
    
    logger.info("All API tests completed successfully")
    return True


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Set up the full real implementation for the assessment recommendation system")
    parser.add_argument("--skip-vector-setup", action="store_true", help="Skip the vector search setup step")
    parser.add_argument("--skip-embeddings", action="store_true", help="Skip the embeddings generation step")
    parser.add_argument("--skip-api-test", action="store_true", help="Skip the API testing step")
    parser.add_argument("--batch-size", type=int, default=25, help="Number of assessments to process in each batch")
    parser.add_argument("--force-embeddings", action="store_true", help="Force regeneration of embeddings for all assessments")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually update the database")
    args = parser.parse_args()
    
    logger.info("Starting setup for real implementation")
    start_time = time.time()
    
    # Step 1: Set up vector search
    if not args.skip_vector_setup:
        vector_success = await setup_vector_search()
        if not vector_success:
            logger.error("Vector search setup failed, continuing with other steps...")
    else:
        logger.info("Skipping vector search setup")
    
    # Step 2: Generate embeddings
    if not args.skip_embeddings:
        embeddings_success = await generate_embeddings(args)
        if not embeddings_success:
            logger.error("Embeddings generation failed, continuing with other steps...")
    else:
        logger.info("Skipping embeddings generation")
    
    # Step 3: Test API endpoints
    if not args.skip_api_test:
        try:
            # Check if API is already running
            import httpx
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get("http://localhost:8000/api/health", timeout=2.0)
                logger.info("API is already running, proceeding with tests")
            except:
                logger.error("API is not running, please start the API before testing")
                logger.info("Run 'python -m backend.main' in a separate terminal to start the API")
                return
            
            api_success = await test_api_endpoints()
            if not api_success:
                logger.error("API testing failed")
        except Exception as e:
            logger.error(f"Error during API testing: {e}")
    else:
        logger.info("Skipping API testing")
    
    # Done
    duration = time.time() - start_time
    logger.info(f"Setup completed in {duration:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main()) 