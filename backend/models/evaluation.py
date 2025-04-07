from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class QueryGroundTruth(BaseModel):
    """Model for a query and its ground truth relevant assessments."""
    id: str = Field(..., description="Unique identifier for the query")
    query: str = Field(..., description="The natural language query text")
    relevant_assessments: List[str] = Field(..., description="List of assessment names that are relevant to the query")
    description: Optional[str] = Field(None, description="Optional description of the query scenario")


class EvaluationResult(BaseModel):
    """Model for evaluation results of a single query."""
    query_id: str = Field(..., description="ID of the evaluated query")
    query_text: str = Field(..., description="Text of the evaluated query")
    recall_at_k: float = Field(..., description="Recall@K for this query")
    precision_at_k: List[float] = Field(..., description="Precision at each position up to K")
    average_precision: float = Field(..., description="Average Precision (AP) for this query")
    recommended_assessments: List[str] = Field(..., description="Names of recommended assessments")
    relevant_recommended: List[str] = Field(..., description="Names of relevant assessments that were recommended")
    total_relevant: int = Field(..., description="Total number of relevant assessments for this query")


class EvaluationSummary(BaseModel):
    """Model for summarizing evaluation results across multiple queries."""
    mean_recall_at_k: float = Field(..., description="Mean Recall@K across all queries")
    mean_average_precision: float = Field(..., description="Mean Average Precision (MAP) across all queries")
    k_value: int = Field(..., description="K value used for the evaluation")
    total_queries: int = Field(..., description="Total number of queries evaluated")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of the evaluation")
    evaluation_results: List[EvaluationResult] = Field(..., description="Detailed results for each query") 