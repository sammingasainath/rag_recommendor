# SHL Assessment Recommendation Engine

## Project Overview
This project implements a Recommendation Engine for SHL's assessment products using Retrieval-Augmented Generation (RAG) techniques. The system helps match job requirements with appropriate SHL assessments, providing detailed explanations for recommendations.

## Features
- Web scraping of SHL's product catalog
- Semantic search using vector embeddings
- LLM-powered recommendation generation
- Modern web interface for user interaction
- Detailed explanation generation for recommendations

## Project Structure
```
shl-recommender/
├── data/                # Data storage
│   ├── raw/            # Raw scraped data
│   ├── processed/      # Cleaned and processed data
│   ├── validated/      # Validated data
│   └── metadata/       # Logs and metadata
├── src/                # Source code
│   ├── scrapers/       # Web scraping modules
│   ├── processors/     # Data processing modules
│   └── validation/     # Data validation modules
├── main.py            # Main execution script
├── requirements.txt   # Project dependencies
└── README.md         # Project documentation
```

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- PostgreSQL with pgvector extension (for Supabase)
- Node.js 18+ (for frontend)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd shl-recommender
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

### Running the Data Collection Pipeline

1. Run the main script:
```bash
python main.py
```

This will:
- Scrape the SHL product catalog
- Process and validate the data
- Store the results in the appropriate directories

## Data Collection Process

### 1. Web Scraping
- Uses Crawl4AI to collect assessment data
- Implements rate limiting and error handling
- Stores raw data in JSON format

### 2. Data Processing
- Cleans and normalizes collected data
- Validates against defined schemas
- Generates processing statistics

### 3. Data Validation
- Ensures data completeness
- Validates relationships
- Generates validation reports

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
flake8
```

### Type Checking
```bash
mypy .
```

## Project Components

### 1. Data Collection
- Web scraping of SHL's product catalog
- Extraction of assessment details
- Collection of metadata and relationships

### 2. Data Processing
- Text cleaning and normalization
- Schema validation
- Error handling and reporting

### 3. Quality Assurance
- Automated testing
- Data validation
- Performance monitoring

## Contributing
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
[Insert License Information]

## Contact
[Insert Contact Information] 