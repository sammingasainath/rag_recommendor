# SHL Assessment Catalog Scraper

A Python package for scraping SHL's assessment catalog using Google's Gemini API for enhanced text extraction and analysis.

## Features

- Asynchronous scraping of SHL's product catalog
- LLM-powered extraction of assessment details using Gemini
- Automatic categorization of assessment types
- Comprehensive data collection including:
  - Assessment descriptions
  - Job levels
  - Languages
  - Test durations
  - Key features
- Data export in both JSON and CSV formats
- Robust error handling and retry mechanisms
- Detailed logging

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd shl_scraper
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the root directory with:
```
GOOGLE_API_KEY=your_gemini_api_key_here
```

## Usage

Run the scraper:
```python
from shl_scraper import SHLScraper
import asyncio

async def main():
    scraper = await SHLScraper.create_and_run()
    stats = scraper.get_statistics()
    print(f"Scraped {stats['total_assessments']} assessments")

if __name__ == "__main__":
    asyncio.run(main())
```

Or use the provided run script:
```bash
python -m shl_scraper.run
```

## Output

The scraper saves data in two formats:
- JSON: `data/raw/shl_assessments_TIMESTAMP.json`
- CSV: `data/raw/shl_assessments_TIMESTAMP.csv`

## Logging

Logs are saved to:
- Console output
- `scraping.log` file

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
black .
```

Run linting:
```bash
flake8
``` 