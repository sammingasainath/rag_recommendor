# SHL Assessment Recommendation Engine - Backend

This is the backend implementation of the SHL Assessment Recommendation Engine, which uses RAG (Retrieval-Augmented Generation) architecture to provide accurate and contextually relevant assessment recommendations.

## Technology Stack

- FastAPI (Python)
- Supabase (PostgreSQL with pgvector)
- Google Gemini API (Embeddings and LLM)
- Docker (optional)

## Setup Instructions

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
- Copy `.env.example` to `.env`
- Fill in the required credentials:
  - `SUPABASE_URL`
  - `SUPABASE_KEY`
  - `GEMINI_API_KEY`

4. Initialize Supabase:
- Run the SQL scripts in `scripts/setup_supabase.sql`
- Configure the Automatic Embeddings feature

5. Start the development server:
```bash
uvicorn main:app --reload
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
backend/
├── core/           # Core configuration
├── data/           # Data files
├── models/         # Pydantic models
├── routers/        # API routes
├── services/       # Business logic
├── utils/          # Utility functions
└── scripts/        # Setup and evaluation scripts
```

## Development

1. Follow the Python code style guide (PEP 8)
2. Write tests for new features
3. Update documentation when making changes

## Testing

Run tests with pytest:
```bash
pytest
```

## Evaluation

Use the evaluation script to measure recommendation quality:
```bash
python scripts/evaluate.py
``` 