# Backend Implementation Plan: SHL Assessment Recommendation Engine

## 1. Overview

This plan details the backend implementation for the SHL Assessment Recommendation Engine. It leverages a RAG architecture using FastAPI (Python) for the API, Supabase with pgvector for data storage and vector search, and Google Gemini APIs for text embedding and recommendation generation. Special attention is given to integrating Supabase's Automatic Embeddings feature with the Gemini embedding model.

## 2. Technology Stack

*   **API Framework**: FastAPI (Python)
*   **Vector Database**: Supabase (PostgreSQL with pgvector extension)
*   **Embedding Model**: Google Gemini Embedding API (e.g., `text-embedding-004`)
*   **Generative LLM**: Google Gemini Pro API (e.g., `gemini-1.5-flash` or `gemini-1.5-pro`)
*   **Libraries**: `fastapi`, `uvicorn`, `supabase-py`, `google-generativeai`, `pandas`, `python-dotenv`
*   **Infrastructure**: Supabase Platform, Deployment platform for FastAPI (e.g., Cloud Run, Render, Fly.io)
*   **Containerization**: Docker (Optional but recommended for deployment)

## 3. Project Structure (Inside `backend/`)

```
backend/
├── .venv/                  # Virtual environment
├── .env                    # Environment variables (API keys, Supabase creds)
├── .gitignore              # Git ignore rules
├── Dockerfile              # For containerization (optional)
├── requirements.txt        # Python dependencies
├── main.py                 # FastAPI app initialization
├── core/
│   └── config.py           # Load environment variables, settings
├── data/
│   └── shl_individual_assessments.csv # Source data (or placed elsewhere)
├── models/
│   ├── assessment.py       # Pydantic models for assessment data
│   └── recommendation.py   # Pydantic models for API request/response
├── routers/
│   ├── assessments.py      # API routes for assessment data management
│   └── recommendations.py  # API routes for generating recommendations
├── services/
│   ├── assessment_service.py # Logic for loading/managing assessment data
│   ├── gemini_service.py     # Logic for interacting with Gemini APIs
│   ├── rag_pipeline.py       # Core RAG orchestration logic
│   └── supabase_service.py   # Logic for interacting with Supabase
├── utils/
│   └── data_parser.py      # Helper functions for parsing CSV data
├── scripts/
│   ├── setup_supabase.sql  # SQL script for initial table/function setup (alternative to manual setup)
│   └── evaluate.py         # Script for running evaluation metrics
└── README.md               # Backend-specific documentation
```

## 4. Supabase Setup & Data Representation

### 4.1. Database Schema (`assessments` table)

```sql
-- Ensure required extensions are enabled
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_net; -- Required for calling external APIs like Gemini from functions/triggers
CREATE EXTENSION IF NOT EXISTS pgmq; -- Required for Supabase Automatic Embeddings queue
-- Might need pg_cron if using cron-based queue processing

-- Main table for assessments
CREATE TABLE public.assessments (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    url TEXT,
    remote_testing BOOLEAN,
    adaptive_irt BOOLEAN,
    test_types TEXT[],
    description TEXT,
    job_levels TEXT[],
    duration_text TEXT, -- Store original text for reference
    duration_minutes INTEGER, -- Parsed numeric duration for filtering
    languages TEXT[],
    key_features TEXT[],
    source TEXT,
    embedding vector(768) NULL, -- Store Gemini embeddings (e.g., text-embedding-004 outputs 768 dimensions)
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Function and Trigger to update 'updated_at' timestamp
CREATE OR REPLACE FUNCTION public.trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON public.assessments
FOR EACH ROW
EXECUTE FUNCTION public.trigger_set_timestamp();

-- Indexes for performance
CREATE INDEX ON public.assessments USING hnsw (embedding vector_cosine_ops); -- HNSW index for vector search
CREATE INDEX idx_assessments_job_levels ON public.assessments USING GIN (job_levels); -- GIN index for array searching
CREATE INDEX idx_assessments_test_types ON public.assessments USING GIN (test_types); -- GIN index for array searching
CREATE INDEX idx_assessments_duration ON public.assessments (duration_minutes); -- B-tree index for range filtering
```

### 4.2. Automatic Embedding Integration (Gemini)

This leverages Supabase's trigger-based asynchronous pattern but adapts it for Gemini.

1.  **Setup Supabase Functions/Triggers:**
    *   Install necessary Supabase extensions (`vector`, `pg_net`, `pgmq`, potentially `pg_cron`).
    *   Implement the standard `util.queue_embeddings` function provided in Supabase documentation, which uses `pgmq` to enqueue jobs.
    *   Create a PL/pgSQL function `public.assessment_embedding_input(rec assessments)` to generate the text input for the embedding model by concatenating relevant fields (e.g., `name`, `description`, `key_features`, `test_types`).

        ```sql
        CREATE OR REPLACE FUNCTION public.assessment_embedding_input(rec assessments)
        RETURNS text
        LANGUAGE plpgsql IMMUTABLE PARALLEL SAFE AS $$
        BEGIN
            RETURN '# ' || rec.name || '\n\n' ||
                   'Description: ' || COALESCE(rec.description, '') || '\n\n' ||
                   'Key Features: ' || array_to_string(COALESCE(rec.key_features, ARRAY[]::text[]), ', ') || '\n\n' ||
                   'Test Types: ' || array_to_string(COALESCE(rec.test_types, ARRAY[]::text[]), ', ') || '\n\n' ||
                   'Job Levels: ' || array_to_string(COALESCE(rec.job_levels, ARRAY[]::text[]), ', ');
        END;
        $$;
        ```
2.  **Embedding Generation Mechanism (Choose One):**
    *   **Option A (Recommended: Supabase Edge Function):**
        *   Create an Edge Function (`gemini-embedder`).
        *   This function is triggered by messages on the `pgmq` queue (via `pg_cron` or another trigger mechanism).
        *   It retrieves the assessment `id` and the text from `assessment_embedding_input`.
        *   Securely fetches the Gemini API Key (e.g., from Supabase Vault).
        *   Calls the Gemini Embedding API (`https://generativelanguage.googleapis.com/.../models/text-embedding-004:embedContent`).
        *   Handles the response, extracts the embedding vector.
        *   Uses the Supabase client (available in Edge Functions) to `UPDATE public.assessments SET embedding = '[vector]' WHERE id = assessment_id;`.
    *   **Option B (Webhook via `pg_net`):**
        *   Modify the `pgmq` processing logic (or the `util.queue_embeddings` function itself if simpler) to use `pg_net.http_post` to call a secure endpoint in your FastAPI backend (e.g., `/webhooks/generate-embedding`).
        *   The FastAPI endpoint receives the `id` and `text`, calls the Gemini API using the Python client, and updates the Supabase record via the Supabase Python client. Requires careful security (e.g., validating requests with a shared secret).
3.  **Attach Triggers to `assessments` Table:**
    *   Create triggers that call `util.queue_embeddings` after `INSERT` and relevant `UPDATE` operations on the `assessments` table, specifying `assessment_embedding_input` as the source function and `embedding` as the target column.

    ```sql
    -- Trigger for insert events
    CREATE TRIGGER embed_assessments_on_insert
    AFTER INSERT ON public.assessments
    FOR EACH ROW
    EXECUTE FUNCTION util.queue_embeddings('assessment_embedding_input', 'embedding');

    -- Trigger for update events on relevant columns
    CREATE TRIGGER embed_assessments_on_update
    AFTER UPDATE OF name, description, key_features, test_types, job_levels -- Columns used in assessment_embedding_input
    ON public.assessments
    FOR EACH ROW
    WHEN (OLD.* IS DISTINCT FROM NEW.*) -- Only if relevant columns changed
    EXECUTE FUNCTION util.queue_embeddings('assessment_embedding_input', 'embedding');
    ```

### 4.3. Data Ingestion API

*   **Endpoint**: `POST /assessments/upload`
*   **Functionality**:
    *   Accepts a CSV file (`shl_individual_assessments.csv` format).
    *   Parses the CSV using `pandas`.
    *   Cleans data: Convert boolean strings to `BOOLEAN`, parse duration text to `duration_minutes` (integer), parse string representations of lists (`"['a','b']"`) into actual lists suitable for `TEXT[]` columns.
    *   Uses Supabase Python client's `upsert` function to add/update records in the `assessments` table based on the `name` column.
    *   **Important**: The `embedding` column is *not* populated here; the triggers handle queuing the embedding generation.

## 5. RAG Pipeline Implementation

*   **Endpoint**: `POST /recommendations`
*   **Request Body**:
    ```json
    {
      "query": "string", // User's natural language query (e.g., job description, requirements)
      "top_k": "integer (optional, default: 10)", // Number of final recommendations
      "filters": { // Optional structured filters
        "job_levels": ["string"],
        "max_duration_minutes": "integer",
        "test_types": ["string"],
        "min_similarity": "float (optional, default: 0.7)" // Threshold for vector search
        // Add other potential filters (languages, remote_testing etc.)
      }
    }
    ```
*   **Response Body**:
    ```json
    {
      "recommendations": [
        {
          "name": "string",
          "url": "string",
          "description": "string",
          "explanation": "string", // LLM-generated explanation
          "similarity_score": "float", // From vector search
          "relevance_score": "float (optional)" // If LLM provides explicit score
          // Include other relevant fields like duration, job_levels etc.
        }
      ]
    }
    ```
*   **Pipeline Steps (`services/rag_pipeline.py`)**:
    1.  **Query Processing**:
        *   Clean the input `query`.
        *   (Optional Advanced) Use Gemini to extract key entities (job title, skills, constraints) if not provided in `filters`.
    2.  **Query Embedding**: Embed the processed `query` using the *same* Gemini model (`text-embedding-004`).
    3.  **Retrieval**:
        *   Call a Supabase database function `match_assessments` via RPC. This function performs a combined vector similarity search and metadata filtering.
        *   **`match_assessments` (PostgreSQL Function):**
            ```sql
            CREATE OR REPLACE FUNCTION public.match_assessments (
              query_embedding vector(768),
              match_threshold float,
              match_count int,
              filter_job_levels text[] default null,
              filter_max_duration integer default null,
              filter_test_types text[] default null
              -- Add other filters as needed
            ) RETURNS TABLE (
                -- Columns matching the required output for context + similarity
                id integer,
                name text,
                url text,
                description text,
                job_levels text[],
                duration_minutes integer,
                test_types text[],
                key_features text[],
                similarity float
            )
            LANGUAGE sql STABLE PARALLEL SAFE AS $$
            SELECT
                a.id,
                a.name,
                a.url,
                a.description,
                a.job_levels,
                a.duration_minutes,
                a.test_types,
                a.key_features,
                1 - (a.embedding <=> query_embedding) AS similarity -- Cosine similarity calculation
            FROM public.assessments a
            WHERE a.embedding IS NOT NULL -- Ensure embedding exists
              AND (1 - (a.embedding <=> query_embedding)) >= match_threshold
              AND (filter_job_levels IS NULL OR a.job_levels && filter_job_levels) -- Array overlap
              AND (filter_max_duration IS NULL OR a.duration_minutes <= filter_max_duration)
              AND (filter_test_types IS NULL OR a.test_types && filter_test_types) -- Array overlap
              -- Add other filter conditions here
            ORDER BY similarity DESC -- Order by similarity score descending
            LIMIT match_count;
            $$;
            ```
        *   Retrieve slightly more candidates than `top_k` (e.g., `top_k * 2` or `top_k + 5`) to give the LLM more context for ranking. Let's call this `retrieved_k`.
    4.  **Context Formulation**: Combine the details of the `retrieved_k` assessments into a structured text block. Include key fields like `name`, `description`, `job_levels`, `duration_minutes`, `test_types`, `key_features`, and the `similarity_score`.
    5.  **Generation & Ranking (Gemini Pro)**:
        *   Craft a detailed prompt for the Gemini generative model:
            *   Set the persona (SHL Assessment Expert).
            *   Provide the original user `query` and `filters`.
            *   Inject the formatted context from Step 4.
            *   Instruct the LLM:
                *   To act as a re-ranker and recommender.
                *   Select the *best* `top_k` assessments from the provided context that *strictly* match the user's query and filters.
                *   Generate a concise `explanation` for each chosen recommendation, justifying its relevance based *only* on the provided context and user query.
                *   Explicitly mention if a recommendation is strong but slightly violates a soft constraint (like duration, if applicable).
                *   Output the results as a JSON list (matching the response model), ordered from most to least relevant.
    6.  **Post-processing**:
        *   Parse the JSON response from Gemini.
        *   Validate the output against the Pydantic response model.
        *   Handle cases where the LLM might fail to generate valid JSON or finds no suitable recommendations.
        *   Return the final list of `top_k` recommendations.

## 6. Matching Strategy

*   **Layer 1: Semantic Matching**: Cosine similarity between the Gemini embedding of the user query and the Gemini embeddings of the assessments (using `assessment_embedding_input`). Handled by `pgvector`'s HNSW index search.
*   **Layer 2: Structured Filtering**: Hard filters applied within the Supabase `match_assessments` function (`WHERE` clause) based on `job_levels`, `duration_minutes`, `test_types`, etc.
*   **Layer 3: LLM Re-ranking & Contextual Matching**: The Gemini generative model re-evaluates the top candidates from the retrieval phase based on the nuances of the user query and the combined context of retrieved documents, generating explanations and implicitly (or explicitly if prompted) ranking them.
*   **Recursion**: Not planned for the initial implementation. Focus on optimizing the single RAG loop.

## 7. Ranking & Re-ranking Approach

1.  **Initial Ranking**: Done by `pgvector` based on cosine similarity during the retrieval step (Layer 1).
2.  **Re-ranking**: Performed by the Gemini generative LLM (Layer 3). The prompt explicitly asks the LLM to select and order the best `top_k` results from the candidates provided in the context, effectively acting as a re-ranker based on deeper contextual understanding.
3.  **(Future Enhancement)**: If LLM re-ranking isn't sufficient, consider adding a dedicated cross-encoder model for pairwise scoring between query and retrieved documents before the LLM step, or prompting the LLM to output explicit relevance scores.

## 8. Evaluation

*   **Metrics**: Mean Recall@K, Mean Average Precision @K (MAP@K) as specified (K=5, K=10).
*   **Test Data**: Use the provided sample queries.
*   **Ground Truth**: **Crucially, requires manual creation of a ground truth dataset.** For each test query, identify the set of "relevant" assessment `name`s from `shl_individual_assessments.csv`. This is subjective and requires domain understanding.
*   **Process**:
    *   Use the `scripts/evaluate.py` script.
    *   For each test query:
        *   Call the `POST /recommendations` endpoint.
        *   Compare the returned list of assessment names against the ground truth list.
        *   Calculate Precision@k, Recall@k for k=1 to K.
        *   Calculate AP@K for the query.
    *   Average Recall@K and AP@K across all test queries to get Mean Recall@K and MAP@K.
*   **Iteration**: Use evaluation results to tune: embedding input function (`assessment_embedding_input`), retrieval `match_threshold` and `retrieved_k`, LLM prompt, potentially filtering logic.

## 9. Next Steps (Immediate Backend Tasks)

1.  **Environment Setup**: Create virtual env, install `requirements.txt`. Set up `.env`.
2.  **Supabase Schema**: Apply the schema, functions, and triggers (either manually via Supabase UI or using `scripts/setup_supabase.sql`). Configure the chosen Gemini embedding mechanism (Edge Function or Webhook).
3.  **Implement Data Ingestion**: Build the `POST /assessments/upload` endpoint and associated service/utils for parsing and loading CSV data.
4.  **Implement RAG Core**: Build the `services/gemini_service.py`, `services/supabase_service.py` (with `match_assessments` RPC call), and `services/rag_pipeline.py`.
5.  **Implement Recommendation API**: Build the `POST /recommendations` endpoint wiring it to the RAG pipeline.
6.  **Initial Testing**: Manually test endpoints. Verify embeddings are being generated in Supabase.
7.  **Develop Evaluation Script**: Create `scripts/evaluate.py` and the ground truth data. 