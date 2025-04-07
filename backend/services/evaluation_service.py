import json
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.models.evaluation import QueryGroundTruth, EvaluationResult, EvaluationSummary
from backend.services.supabase_service import supabase_service
from backend.services.rag_pipeline import rag_pipeline
from backend.core.config import settings

logger = logging.getLogger(__name__)

class EvaluationService:
    """Service for evaluating recommendation quality against ground truth data."""
    
    def __init__(self):
        self.ground_truth_path = os.path.join(settings.DATA_DIR, "evaluation", "ground_truth.json")
        self.results_path = os.path.join(settings.DATA_DIR, "evaluation", "results")
        self._ensure_directories()
        self.ground_truth_data = self._load_ground_truth()
    
    def _ensure_directories(self):
        """Ensure that the evaluation directories exist."""
        os.makedirs(os.path.join(settings.DATA_DIR, "evaluation"), exist_ok=True)
        os.makedirs(self.results_path, exist_ok=True)
    
    def _load_ground_truth(self) -> Dict[str, QueryGroundTruth]:
        """Load ground truth data from file."""
        if not os.path.exists(self.ground_truth_path):
            logger.warning(f"Ground truth file not found: {self.ground_truth_path}")
            return {}
        
        try:
            with open(self.ground_truth_path, 'r') as f:
                data = json.load(f)
                return {item["id"]: QueryGroundTruth(**item) for item in data}
        except Exception as e:
            logger.error(f"Error loading ground truth data: {e}")
            return {}
    
    def save_ground_truth(self, ground_truth_data: List[QueryGroundTruth]):
        """Save ground truth data to file."""
        try:
            with open(self.ground_truth_path, 'w') as f:
                json.dump([gt.dict() for gt in ground_truth_data], f, indent=2)
            self.ground_truth_data = {gt.id: gt for gt in ground_truth_data}
            logger.info(f"Ground truth data saved to {self.ground_truth_path}")
        except Exception as e:
            logger.error(f"Error saving ground truth data: {e}")
    
    async def evaluate_query(self, query_id: str, k: int = 10) -> Optional[EvaluationResult]:
        """Evaluate a single query against ground truth."""
        if query_id not in self.ground_truth_data:
            logger.error(f"Query ID not found in ground truth: {query_id}")
            return None
        
        ground_truth = self.ground_truth_data[query_id]
        
        # Get recommendations for the query
        try:
            recommendations = await rag_pipeline.get_recommendations(
                query=ground_truth.query,
                top_k=k
            )
            
            # Get names of recommended assessments
            recommended_names = [rec.name for rec in recommendations]
            relevant_names = ground_truth.relevant_assessments
            
            # Calculate relevant assessments that were recommended
            relevant_recommended = [rec_name for rec_name in recommended_names if rec_name in relevant_names]
            
            # Calculate Recall@K
            recall = len(relevant_recommended) / len(relevant_names) if relevant_names else 0
            
            # Calculate Precision@k at each position
            precision_at_positions = []
            for i in range(1, len(recommended_names) + 1):
                recommended_so_far = recommended_names[:i]
                relevant_so_far = [rec_name for rec_name in recommended_so_far if rec_name in relevant_names]
                precision = len(relevant_so_far) / len(recommended_so_far) if recommended_so_far else 0
                precision_at_positions.append(precision)
            
            # Calculate Average Precision (AP)
            ap = 0
            num_relevant = 0
            for i, rec_name in enumerate(recommended_names):
                if rec_name in relevant_names:
                    num_relevant += 1
                    ap += num_relevant / (i + 1)
            
            ap = ap / len(relevant_names) if relevant_names else 0
            
            # Create evaluation result
            result = EvaluationResult(
                query_id=query_id,
                query_text=ground_truth.query,
                recall_at_k=recall,
                precision_at_k=precision_at_positions,
                average_precision=ap,
                recommended_assessments=recommended_names,
                relevant_recommended=relevant_recommended,
                total_relevant=len(relevant_names)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating query {query_id}: {e}")
            return None
    
    async def evaluate_all(self, k: int = 10) -> Optional[EvaluationSummary]:
        """Evaluate all queries in the ground truth dataset."""
        if not self.ground_truth_data:
            logger.error("No ground truth data available for evaluation")
            return None
        
        evaluation_results = []
        recall_sum = 0
        ap_sum = 0
        
        for query_id in self.ground_truth_data:
            result = await self.evaluate_query(query_id, k)
            if result:
                evaluation_results.append(result)
                recall_sum += result.recall_at_k
                ap_sum += result.average_precision
        
        if not evaluation_results:
            logger.error("No evaluation results produced")
            return None
        
        # Calculate mean metrics
        mean_recall = recall_sum / len(evaluation_results)
        mean_ap = ap_sum / len(evaluation_results)
        
        # Create summary
        summary = EvaluationSummary(
            mean_recall_at_k=mean_recall,
            mean_average_precision=mean_ap,
            k_value=k,
            total_queries=len(evaluation_results),
            evaluation_results=evaluation_results
        )
        
        # Save results
        self._save_evaluation_results(summary)
        
        return summary
    
    def _save_evaluation_results(self, summary: EvaluationSummary):
        """Save evaluation results to file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_{timestamp}.json"
        filepath = os.path.join(self.results_path, filename)
        
        try:
            # Convert summary to dict and then convert the datetime to string
            summary_dict = summary.dict()
            
            # Handle the timestamp field explicitly
            if isinstance(summary_dict['timestamp'], datetime):
                summary_dict['timestamp'] = summary_dict['timestamp'].isoformat()
            
            with open(filepath, 'w') as f:
                json.dump(summary_dict, f, indent=2)
            logger.info(f"Evaluation results saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving evaluation results: {e}")
    
    def get_saved_evaluations(self) -> List[Dict[str, Any]]:
        """Get a list of saved evaluation results."""
        results = []
        
        try:
            for filename in os.listdir(self.results_path):
                if filename.endswith('.json') and filename.startswith('evaluation_'):
                    filepath = os.path.join(self.results_path, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        # Add the filename for reference
                        data['filename'] = filename
                        results.append(data)
            
            # Sort by timestamp descending
            results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return results
        except Exception as e:
            logger.error(f"Error loading saved evaluations: {e}")
            return []


# Create a singleton instance
evaluation_service = EvaluationService() 