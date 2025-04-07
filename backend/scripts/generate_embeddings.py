#!/usr/bin/env python
"""
Script to generate and update embeddings for all assessments in the database.
This script requires both Supabase and Gemini API access to function.

Usage:
    python -m backend.scripts.generate_embeddings

Options:
    --batch-size INT      Number of assessments to process in each batch [default: 25]
    --force               Force regeneration of embeddings for all assessments
    --dry-run             Don't actually update the database, just print what would be done
"""

import argparse
import asyncio
import logging
import sys
import time
from typing import List, Dict, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("generate_embeddings")

# Add parent directory to path
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.core.config import settings
from backend.services.supabase_service import SupabaseService
from backend.services.gemini_service import gemini_service


async def get_all_assessments(supabase: SupabaseService) -> List[Dict[str, Any]]:
    """Retrieve all assessments from the database."""
    logger.info("Retrieving all assessments from the database...")
    
    # Use the direct client rather than the service method to get raw data
    if not supabase.initialized or not supabase.client:
        logger.error("Supabase service not initialized")
        return []
    
    try:
        result = supabase.client.table(settings.SUPABASE_ASSESSMENTS_TABLE).select('*').execute()
        
        if hasattr(result, 'get') and result.get('error'):
            logger.error(f"Error retrieving assessments: {result.get('error')}")
            return []
            
        logger.info(f"Retrieved {len(result.data)} assessments")
        return result.data
    except Exception as e:
        logger.error(f"Error retrieving assessments: {e}")
        return []


def create_text_for_embedding(assessment: Dict[str, Any]) -> str:
    """
    Create a text representation of an assessment for embedding.
    This combines the key fields into a single text string.
    """
    parts = []
    
    # Primary fields
    if assessment.get('name'):
        parts.append(f"Name: {assessment['name']}")
    
    if assessment.get('description'):
        parts.append(f"Description: {assessment['description']}")
    
    # Test types and job levels
    if assessment.get('test_types') and isinstance(assessment['test_types'], list):
        parts.append(f"Test Types: {', '.join(assessment['test_types'])}")
    
    if assessment.get('job_levels') and isinstance(assessment['job_levels'], list):
        parts.append(f"Job Levels: {', '.join(assessment['job_levels'])}")
    
    # Duration information
    if assessment.get('duration_text'):
        parts.append(f"Duration: {assessment['duration_text']}")
    
    # Key features
    if assessment.get('key_features') and isinstance(assessment['key_features'], list):
        parts.append(f"Key Features: {', '.join(assessment['key_features'])}")
    
    # Languages
    if assessment.get('languages') and isinstance(assessment['languages'], list):
        parts.append(f"Languages: {', '.join(assessment['languages'])}")
    
    # Additional flags
    flags = []
    if assessment.get('remote_testing'):
        flags.append("Remote Testing")
    if assessment.get('adaptive_irt'):
        flags.append("Adaptive IRT")
    if assessment.get('is_untimed'):
        flags.append("Untimed")
    if assessment.get('is_variable_duration'):
        flags.append("Variable Duration")
    
    if flags:
        parts.append(f"Features: {', '.join(flags)}")
    
    return "\n".join(parts)


async def process_batch(
    supabase: SupabaseService, 
    assessments: List[Dict[str, Any]], 
    batch_num: int, 
    total_batches: int,
    dry_run: bool = False
) -> int:
    """Process a batch of assessments to generate and store embeddings."""
    batch_size = len(assessments)
    logger.info(f"Processing batch {batch_num}/{total_batches} with {batch_size} assessments")
    
    success_count = 0
    for i, assessment in enumerate(assessments):
        assessment_id = assessment.get('id')
        
        # Create text for embedding
        text = create_text_for_embedding(assessment)
        
        try:
            # Generate embedding
            embedding = await gemini_service.get_embedding(text)
            
            if not embedding:
                logger.error(f"Failed to generate embedding for assessment {assessment_id}")
                continue
            
            logger.info(f"Generated embedding for assessment {assessment_id} ({i+1}/{batch_size})")
            
            # Update the assessment with the embedding
            if not dry_run:
                if not supabase.initialized or not supabase.client:
                    logger.error("Supabase service not initialized")
                    continue
                
                try:
                    result = supabase.client.table(settings.SUPABASE_ASSESSMENTS_TABLE).update({
                        settings.SUPABASE_EMBEDDINGS_COLUMN: embedding
                    }).eq('id', assessment_id).execute()
                    
                    if hasattr(result, 'get') and result.get('error'):
                        logger.error(f"Error updating embedding for assessment {assessment_id}: {result.get('error')}")
                        continue
                    
                    logger.info(f"Updated embedding for assessment {assessment_id}")
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error updating embedding for assessment {assessment_id}: {e}")
            else:
                logger.info(f"DRY RUN: Would update embedding for assessment {assessment_id}")
                success_count += 1
        
        except Exception as e:
            logger.error(f"Error processing assessment {assessment_id}: {e}")
        
        # Add a small delay to avoid rate limiting
        if i < batch_size - 1:
            await asyncio.sleep(0.2)
    
    return success_count


async def main():
    """Main function to generate and update embeddings."""
    parser = argparse.ArgumentParser(description="Generate embeddings for assessments")
    parser.add_argument("--batch-size", type=int, default=25, help="Number of assessments to process in each batch")
    parser.add_argument("--force", action="store_true", help="Force regeneration of embeddings for all assessments")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually update the database")
    args = parser.parse_args()
    
    if settings.USE_MOCK_DATA:
        logger.error("Cannot generate real embeddings in mock mode - disable USE_MOCK_DATA in settings")
        return
    
    logger.info("Starting embedding generation process")
    
    # Initialize services
    supabase = SupabaseService()
    
    if not supabase.initialized:
        logger.error("Failed to initialize Supabase service")
        return
    
    # Test Gemini service
    try:
        await gemini_service._test_connection()
        logger.info("Gemini service connection test successful")
    except Exception as e:
        logger.error(f"Gemini service connection test failed: {e}")
        return
    
    # Get all assessments
    assessments = await get_all_assessments(supabase)
    
    if not assessments:
        logger.error("No assessments found in the database")
        return
    
    total_assessments = len(assessments)
    logger.info(f"Found {total_assessments} assessments to process")
    
    # If not forcing regeneration, filter to assessments without embeddings
    if not args.force:
        assessments_without_embeddings = [
            a for a in assessments 
            if not a.get(settings.SUPABASE_EMBEDDINGS_COLUMN) or len(a.get(settings.SUPABASE_EMBEDDINGS_COLUMN, [])) == 0
        ]
        
        if len(assessments_without_embeddings) < total_assessments:
            logger.info(f"Filtered to {len(assessments_without_embeddings)} assessments without embeddings")
            logger.info(f"Use --force to regenerate all embeddings")
            assessments = assessments_without_embeddings
    
    # Prepare batches
    batch_size = args.batch_size
    batches = [assessments[i:i + batch_size] for i in range(0, len(assessments), batch_size)]
    total_batches = len(batches)
    
    if args.dry_run:
        logger.info("DRY RUN MODE: No actual updates will be made to the database")
    
    # Process batches
    total_success = 0
    start_time = time.time()
    
    for i, batch in enumerate(batches):
        batch_success = await process_batch(supabase, batch, i + 1, total_batches, args.dry_run)
        total_success += batch_success
        
        # Add a small delay between batches
        if i < total_batches - 1:
            await asyncio.sleep(1)
    
    duration = time.time() - start_time
    logger.info(f"Embedding generation completed in {duration:.2f} seconds")
    logger.info(f"Successfully processed {total_success}/{len(assessments)} assessments")


if __name__ == "__main__":
    asyncio.run(main()) 