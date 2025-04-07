# Backend Documentation: SHL Assessment Recommendation Engine

## 1. Overview

This document details the architecture, implementation, and rationale behind the backend system for the SHL Assessment Recommendation Engine. The primary goal of the backend is to provide an API endpoint that accepts natural language queries describing assessment needs and returns a ranked list of relevant SHL assessments, incorporating various filtering options.

The system leverages a combination of a modern web framework (FastAPI), a powerful database (PostgreSQL with `pgvector`), and Large Language Models (LLMs) via the Google Generative AI API for semantic understanding and response generation.

## 2. Problem Approach & Design

The core problem is to match user needs, expressed in natural language, with a catalog of assessments, each having structured attributes and descriptive text. The chosen approach is a Retrieval-Augmented Generation (RAG) pattern:

1.  **Understanding the Query:** User queries are converted into semantic vector embeddings using an LLM (Google's `text-embedding-004`).
2.  **Retrieval (Semantic Search):** This query embedding is used to search a database of pre-computed assessment embeddings using vector similarity search (`pgvector`'s cosine distance). This efficiently finds assessments that are semantically similar to the user's request.
3.  **Filtering:** The search results are further filtered based on structured criteria provided in the API request (e.g., `max_duration_minutes`, `job_levels`, `test_types`, `remote_testing`). This filtering is integrated directly into the database query for efficiency.
4.  **Re-ranking/Generation (Optional but Implicit):** While not explicitly implemented as a separate re-ranking step in this version, the initial retrieval provides a relevance-ranked list based on semantic similarity. The current implementation uses the top N results from the filtered vector search. (A future enhancement could involve using another LLM call to re-rank or synthesize the final recommendations based on the retrieved candidates and the original query).
5.  **Response Formatting:** The final list of recommended assessments is formatted according to the defined API response models.

## 3. Data Handling

### 3.1. Data Loading & Preparation

-   **Source:** Assessment data is assumed to be initially available in a structured format (e.g., CSV). The `backend/scripts/load_data.py` script handles loading this data (specifically from `backend/data/assessments.csv`) into the PostgreSQL database.
-   **Preprocessing:** The script performs basic cleaning and prepares the data for insertion, potentially combining fields if needed for embedding generation (handled within the embedding script).

### 3.2. Data Representation

-   **Database:** PostgreSQL is used as the primary data store.
-   **Schema:** The `assessments` table schema is defined in `backend/scripts/setup_supabase.sql`. It includes:
    -   Standard assessment attributes (id, name, description, url, etc.).
    -   Specific filterable fields (job\_levels, test\_types, duration\_minutes, languages, remote\_testing, etc.). Note the evolution of duration handling from text/min/max to a single `duration_minutes` column, addressed via schema migration logic within the setup script.
    -   An `embedding` column of type `vector(768)` (using the `pgvector` extension) to store the semantic embeddings.
-   **Embeddings:**
    -   Semantic vector embeddings are generated for each assessment's relevant text fields (e.g., name, description).
    -   The `backend/scripts/generate_embeddings.py` script handles this process. It fetches assessments from the database, generates embeddings using the `GeminiEmbeddingService`, and updates the corresponding records in the `assessments` table.
    -   The `--force` flag allows re-generation of embeddings for all assessments.

### 3.3. Data Searching & Filtering

-   **Vector Search:** The `pgvector` extension enables efficient similarity search using the `embedding` column. An HNSW index (`hnsw_index`) is created on this column (`backend/scripts/setup_supabase.sql`) to accelerate searches.
-   **`match_assessments` Function:** A custom PostgreSQL function (`match_assessments`) is defined in `backend/scripts/setup_supabase.sql`. This function encapsulates the core search and filtering logic:
    -   Takes `query_embedding`, `match_threshold`, `match_count`, and various filter parameters as input.
    -   Performs a vector similarity search (cosine distance) against the `assessments` table.
    -   Applies filters based on the provided parameters (job levels, test types, duration, languages, remote testing).
    -   Returns a table containing matching assessments and their similarity scores.
    -   This function is called via RPC (Remote Procedure Call) by the backend service (`SupabaseService`).
-   **Filtering Implementation:** Filters are applied *within* the database function, making the retrieval process efficient by reducing the amount of data transferred back to the application.

## 4. Technology Stack & Libraries

-   **Web Framework:** FastAPI (`main.py`, `routers/`) - Chosen for its high performance, asynchronous capabilities, automatic OpenAPI/Swagger documentation, and Pydantic integration.
-   **Data Validation:** Pydantic (`models/`) - Used extensively for defining request/response models, ensuring data consistency and providing clear API contracts. The use of `Any` for `id` fields in `AssessmentInDB` and `AssessmentResponse` was a workaround to handle integer IDs coming from the database while initially expecting strings.
-   **Database:** PostgreSQL + `pgvector` extension - A robust relational database with powerful vector search capabilities. Managed via Supabase in this deployment context, but the core is PostgreSQL.
-   **Database Interaction:**
    -   `psycopg2-binary` (`scripts/setup_database.py`): Used for direct database connections during setup script execution.
    -   `supabase-py` (`services/supabase_service.py`): Used for runtime interaction with the Supabase backend (specifically for calling the `match_assessments` RPC function).
-   **LLM Integration:** `google-generativeai` (`services/gemini_service.py`) - Used to interact with the Google Generative AI API for:
    -   Generating text embeddings (`text-embedding-004` model).
    -   Potentially generating textual explanations or summaries (though the primary use currently seems to be embedding generation based on logs).
-   **Configuration:** `python-dotenv` - Manages environment variables loaded from the `.env` file (API keys, database credentials).
-   **Server:** Uvicorn - ASGI server used to run the FastAPI application.
-   **Logging:** Python's built-in `logging` module - Configured in `main.py` to provide basic request and service-level logging.

## 5. Evaluation & Tracing

-   **Current State:** Formal evaluation frameworks (e.g., RAGAS, LangSmith) or dedicated tracing solutions were not integrated in this development cycle.
-   **Evaluation Method:** Evaluation was primarily conducted through:
    -   **Manual API Testing:** Using tools like `Invoke-RestMethod` (PowerShell) or Swagger UI (provided by FastAPI) to send various queries and filter combinations to the `/api/recommendations` endpoint and verifying the responses.
    -   **Log Inspection:** Monitoring the application logs (as seen in the provided `manually_added_selection`) to track the flow of requests, embedding generation, database interactions, and timings.
    -   **Database Inspection:** Directly querying the database to verify data loading, embedding generation, and the results of the `match_assessments` function.
-   **Future Enhancements:**
    -   Integrate a tracing library (like OpenTelemetry) to get finer-grained insights into request latency across services (API, LLM, Database).
    -   Develop an evaluation dataset with sample queries and expected relevant assessments.
    -   Implement automated tests that run these evaluations against the API to measure retrieval metrics (e.g., precision, recall, MRR) and ensure regressions are caught.

## 6. Scalability Considerations

-   **FastAPI:** Being an ASGI framework, FastAPI handles I/O-bound operations (like waiting for database or LLM API responses) asynchronously, allowing it to serve many concurrent requests efficiently.
-   **PostgreSQL:** A mature and scalable database. Performance can be further tuned with configuration, and read replicas can be added if needed.
-   **`pgvector` Indexing:** The HNSW index significantly speeds up vector search, but index build time and memory usage can grow with data size. Parameters might need tuning for larger datasets.
-   **LLM API:** External API calls (Gemini) are subject to rate limits and latency. Caching strategies (e.g., caching embeddings for identical queries) could be implemented if needed.
-   **Stateless Application:** The backend API itself is largely stateless, making it easier to scale horizontally by running multiple instances behind a load balancer.

## 7. Data Updates & Maintenance

-   **Adding/Updating Data:**
    1.  Update the source data file (e.g., `backend/data/assessments.csv`).
    2.  Run `python -m backend.scripts.load_data` to load the new/updated data into the database. This script would need logic to handle updates (e.g., based on a unique assessment identifier) or potentially clear and reload data.
    3.  Run `python -m backend.scripts.generate_embeddings --force` (or modify it to only process new/updated records) to generate and store embeddings for the affected assessments.
-   **Schema Changes:** Modify the `backend/scripts/setup_supabase.sql` script and re-run the `backend/scripts/setup_database.py` script. The setup script includes logic (`DROP FUNCTION IF EXISTS`, `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`) to handle re-running and making schema changes more idempotent, reducing manual intervention.
-   **Dependency Management:** `requirements.txt` lists the necessary Python packages.

## 8. Developer Experience

-   **FastAPI Auto-Docs:** Automatic generation of interactive Swagger UI (`/docs`) and ReDoc (`/redoc`) provides instant API documentation and testing capabilities.
-   **Pydantic Models:** Enforce clear data contracts, improve code readability, and provide validation errors.
-   **Modular Structure:** Code is organized into logical directories (`routers`, `services`, `models`, `scripts`, `utils`).
-   **Setup Scripts:** `setup_database.py` automates the database schema and function creation, simplifying environment setup.
-   **Environment Variables:** `.env` file centralizes configuration, separating secrets and settings from code. `.env.example` provides a template.
-   **Logging:** Provides visibility into the application's runtime behavior for debugging.

## 9. User Experience (API Consumer)

-   **Clear Endpoint:** A single primary endpoint (`/api/recommendations`) simplifies interaction.
-   **Natural Language Query:** Accepts user needs in plain English.
-   **Flexible Filtering:** Allows users to refine results based on multiple criteria simultaneously.
-   **Structured Response:** Returns well-defined JSON responses (validated by `RecommendationResponse` Pydantic model) containing relevant assessment details and metadata.
-   **Health Check:** `/api/health` endpoint allows simple monitoring of service availability.

## 10. Other Implementation Details & Notes

-   **SQL Function (`match_assessments`):** Centralizing the core search and filtering logic in a database function simplifies the application code and leverages the database's efficiency.
-   **Error Handling:** FastAPI provides default exception handling. Specific error handling could be added for database connection issues or LLM API failures. The setup script includes basic error handling during SQL statement execution.
-   **ID Type Handling:** The change from `str` to `Any` for `id` fields in Pydantic models was a pragmatic fix for a type mismatch between the database (integer) and the initial model definition. A more robust solution might involve type casting either in the SQL function or upon receiving data in the service layer.
-   **Git Usage:** The logs show basic Git usage (`add`, `commit`, `push`) for version control.
-   **`.gitignore`:** Properly configured to exclude virtual environments, `.env` files, cache files, etc.
-   **`Implementation_plan_backend.md`:** Contains initial planning notes (though not part of the executable code). 