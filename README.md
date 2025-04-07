# SHL Assessment Recommendation Engine

## Project Overview

This is a comprehensive Retrieval-Augmented Generation (RAG) system that helps users find the most relevant SHL assessments based on their specific requirements. The engine combines semantic search with advanced filtering capabilities to deliver personalized assessment recommendations.

The system uses a vector database for semantic search and a Large Language Model (LLM) for generating recommendations and explanations. It features a modern web interface built with Streamlit and a powerful API backend developed with FastAPI.

## Key Features

- **Semantic Search**: Converts natural language queries into vector embeddings for similarity matching
- **Intelligent Filtering**: Filter assessments by job level, test type, duration, languages, and remote testing options
- **Personalized Recommendations**: Leverages LLM capabilities to generate tailored recommendations
- **Interactive UI**: User-friendly interface with real-time filtering and visualization
- **REST API**: Well-documented API for integration with other systems
- **Performance Metrics**: Evaluation tools to measure and improve recommendation quality

## System Architecture

### Backend (FastAPI)

```
backend/
├── core/              # Core configuration and settings
├── data/              # Assessment data storage
├── models/            # Pydantic models for data validation
├── routers/           # API endpoint definitions
├── scripts/           # Data loading and setup scripts  
├── services/          # Core business logic and integrations
│   ├── gemini_service.py       # Google Generative AI integration
│   ├── rag_pipeline.py         # Main RAG implementation
│   ├── supabase_service.py     # Vector database service
│   └── evaluation_service.py   # Metrics and evaluation
└── utils/             # Utility functions
```

### Frontend (Streamlit)

```
frontend/
├── app.py             # Main Streamlit application
├── admin.py           # Admin interface for data management
└── requirements.txt   # Frontend dependencies
```

## Technology Stack

- **Backend**: 
  - FastAPI (API framework)
  - Google Generative AI (LLM and embeddings)
  - PostgreSQL with pgvector (vector database)
  - Supabase (managed database service)
  - Pydantic (data validation)

- **Frontend**:
  - Streamlit (web interface)
  - Plotly (data visualization)
  - Pandas (data manipulation)

## How It Works

### RAG Pipeline

1. **Query Embedding**: User queries are converted to vector embeddings using Google's text-embedding-004 model
2. **Retrieval**: The query embedding is compared to pre-computed assessment embeddings using cosine similarity
3. **Filtering**: Results are filtered based on user specifications (job level, test type, etc.)
4. **Recommendation Generation**: The LLM evaluates and ranks candidate assessments based on relevance
5. **Response Formatting**: Final recommendations are returned with explanations and metadata

### Vector Search Implementation

The system uses PostgreSQL with the pgvector extension for efficient vector similarity search. A custom SQL function (`match_assessments`) is created for combined vector search and filtering:

```sql
CREATE OR REPLACE FUNCTION match_assessments(
  query_embedding vector(768),
  match_threshold float DEFAULT 0.7,
  match_count int DEFAULT 10,
  filter_job_levels text[] DEFAULT NULL,
  filter_test_types text[] DEFAULT NULL,
  filter_max_duration int DEFAULT NULL,
  filter_languages text[] DEFAULT NULL,
  filter_remote_testing boolean DEFAULT NULL
) RETURNS TABLE (
  id int,
  name text,
  url text,
  description text,
  similarity float,
  -- Additional fields returned
) LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY 
  SELECT 
    a.id, 
    a.name,
    a.url,
    a.description,
    1 - (a.embedding <=> query_embedding) as similarity,
    -- Additional fields
  FROM 
    assessments a
  WHERE 
    -- Filter conditions applied here
    1 - (a.embedding <=> query_embedding) > match_threshold
  ORDER BY 
    similarity DESC
  LIMIT 
    match_count;
END;
$$;
```

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Node.js 18+ (optional, for development)
- PostgreSQL with pgvector extension
- Supabase account (or self-hosted PostgreSQL)
- Google Generative AI API key

### Environment Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd shl-recommendation-engine
```

2. Set up backend:
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up frontend:
```bash
cd frontend
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
# In backend directory
cp .env.example .env
# Edit .env with your API keys and database credentials
```

5. Load and prepare data:
```bash
python -m scripts.setup_database
python -m scripts.load_data
python -m scripts.generate_embeddings
```

### Running the Application

1. Start the backend (from backend directory):
```bash
uvicorn main:app --reload
```

2. Start the frontend (from frontend directory):
```bash
streamlit run app.py
```

3. Access the application:
   - Frontend: http://localhost:8501
   - API documentation: http://localhost:8000/docs

## API Documentation

### Main Endpoints

#### GET /api/health
Health check endpoint to verify the API is running.

#### POST /api/recommendations
Get assessment recommendations based on a natural language query and optional filters.

Request body:
```json
{
  "query": "I need a cognitive assessment for senior software engineers",
  "top_k": 5,
  "filters": {
    "job_levels": ["Senior"],
    "test_types": ["Cognitive", "Technical Skill"],
    "max_duration_minutes": 60,
    "remote_testing": true,
    "languages": ["English"],
    "min_similarity": 0.7
  }
}
```

Response:
```json
{
  "recommendations": [
    {
      "id": 123,
      "name": "Example Assessment",
      "description": "Description of the assessment",
      "url": "/assessments/example",
      "similarity_score": 0.92,
      "relevance_score": 0.92,
      "explanation": "This assessment is relevant because...",
      "job_levels": ["Senior"],
      "test_types": ["Cognitive"],
      "remote_testing": true,
      "languages": ["English"],
      "duration_text": "45 minutes"
    }
  ],
  "processing_time": 0.45,
  "total_assessments": 50
}
```

## Evaluation and Metrics

The system includes an evaluation framework to measure recommendation quality:

- **Top-K Accuracy**: Percentage of queries where the correct assessment appears in top K results
- **Mean Reciprocal Rank (MRR)**: Measures where in the ranking the first relevant result appears
- **Mean Average Precision (MAP)**: Measures precision at different recall levels

## Future Enhancements

- Implement hybrid search (combining keyword and vector search)
- Add user feedback collection for continuous improvement
- Support multi-language queries and responses
- Implement caching for improved performance
- Add batch recommendation capabilities

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[Specify License Information]

## Contact

[Specify Contact Information] 