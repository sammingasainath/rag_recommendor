#!/usr/bin/env python

"""
Script to generate and store embeddings for all assessments in the Supabase database.
This script will:
1. Get all assessments from the database
2. Generate embeddings for each assessment
3. Update the assessments with their embeddings

Usage:
    python -m scripts.generate_embeddings [--force] [--batch-size N]

Arguments:
    --force: Force regeneration of embeddings even if they already exist
    --batch-size: Number of embeddings to process at once (default: 20)
"""

import os
import sys
import asyncio
import argparse
import logging
from typing import List, Dict, Any
import importlib

# Ensure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.config import settings
from backend.services.gemini_service import gemini_service
from backend.services.supabase_service import supabase_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("embedding_generator")


async def get_assessments():
    """Get all assessments from the database."""
    if not supabase_service.initialized or not supabase_service.client:
        logger.error("Supabase service not initialized. Check your API keys and connection.")
        sys.exit(1)
    
    try:
        logger.info("Fetching all assessments from the database...")
        result = supabase_service.client.table(supabase_service.assessments_table).select('*').execute()
        
        if hasattr(result, 'get') and result.get('error'):
            raise RuntimeError(f"Error fetching assessments: {result.get('error')}")
        
        assessments = result.data
        logger.info(f"Found {len(assessments)} assessments")
        return assessments
    except Exception as e:
        logger.error(f"Error fetching assessments: {e}")
        sys.exit(1)


async def generate_embedding_for_assessment(assessment: Dict[str, Any]):
    """Generate an embedding for a single assessment."""
    description = assessment.get('description', '')
    name = assessment.get('name', '')
    
    if not description and not name:
        logger.warning(f"Assessment {assessment.get('id')} has no text to embed")
        return None
    
    # Create a comprehensive text representation for better embedding
    embed_text = f"Assessment: {name}\n\nDescription: {description}\n\n"
    
    # Add test types if available
    test_types = assessment.get('test_types', [])
    if test_types:
        embed_text += f"Test Types: {', '.join(test_types)}\n\n"
    
    # Add job levels if available
    job_levels = assessment.get('job_levels', [])
    if job_levels:
        embed_text += f"Job Levels: {', '.join(job_levels)}\n\n"
    
    # Add key features if available
    key_features = assessment.get('key_features', [])
    if key_features:
        embed_text += f"Key Features: {', '.join(key_features)}\n\n"
    
    try:
        embedding = await gemini_service.get_embedding(embed_text)
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding for assessment {assessment.get('id')}: {e}")
        return None


async def generate_embeddings(assessments: List[Dict[str, Any]], force: bool = False, batch_size: int = 20):
    """Generate embeddings for all assessments and update the database."""
    logger.info(f"Generating embeddings for {len(assessments)} assessments (force={force}, batch_size={batch_size})...")
    
    if settings.USE_MOCK_DATA:
        logger.warning("Mock mode is enabled. Using mock embeddings.")
    
    # Filter assessments that need embeddings
    to_process = []
    for assessment in assessments:
        if force or not assessment.get(supabase_service.embeddings_column):
            to_process.append(assessment)
    
    logger.info(f"{len(to_process)} assessments need embeddings")
    
    if not to_process:
        logger.info("No assessments need embeddings. Exiting.")
        return
    
    # Process in batches
    total_success = 0
    total_error = 0
    
    for i in range(0, len(to_process), batch_size):
        batch = to_process[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(to_process) + batch_size - 1)//batch_size}...")
        
        # Generate embeddings
        embeddings = []
        filtered_batch = []
        
        for assessment in batch:
            embedding = await generate_embedding_for_assessment(assessment)
            if embedding:
                embeddings.append(embedding)
                filtered_batch.append(assessment)
            else:
                total_error += 1
        
        if not filtered_batch:
            logger.warning("No valid embeddings generated in this batch. Skipping update.")
            continue
        
        # Update the database
        try:
            result = await supabase_service.update_all_assessment_embeddings(filtered_batch, embeddings)
            total_success += result["success_count"]
            total_error += result["error_count"]
            logger.info(f"Batch update: {result['success_count']} success, {result['error_count']} errors")
        except Exception as e:
            logger.error(f"Error updating batch: {e}")
            total_error += len(filtered_batch)
    
    logger.info(f"Embedding generation complete: {total_success} success, {total_error} errors")


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Generate and store embeddings for assessments.")
    parser.add_argument("--force", action="store_true", help="Force regeneration of embeddings")
    parser.add_argument("--batch-size", type=int, default=20, help="Batch size for processing")
    args = parser.parse_args()
    
    # Check if Gemini API is available
    if not gemini_service.initialized and not settings.USE_MOCK_DATA:
        logger.error("Gemini API not initialized. Check your API key.")
        sys.exit(1)
    
    # Get all assessments
    assessments = await get_assessments()
    
    # Generate and store embeddings
    await generate_embeddings(assessments, force=args.force, batch_size=args.batch_size)
    
    logger.info("Script execution complete")


if __name__ == "__main__":
    asyncio.run(main()) 