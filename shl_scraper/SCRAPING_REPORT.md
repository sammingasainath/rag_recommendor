# SHL Assessment Catalog Scraper: Development Report

## 1. Project Goal

The primary goal of this project was to develop a web scraper capable of extracting comprehensive information about assessments listed in the SHL Talent Assessment Catalog. This included both "Pre-packaged Job Solutions" and "Individual Test Solutions". The extracted data needed to be structured and saved in accessible formats (JSON and CSV) for further analysis or use in a downstream application like a Recommendation Engine.

## 2. Methodology

The development followed an iterative and adaptive process:

1.  **Initial Setup:** Started by setting up the basic project structure (`shl_scraper` package) and configuring logging.
2.  **Basic Catalog Scraping:** Implemented initial logic to fetch and parse the main catalog pages, extracting basic assessment details like name and URL. This was initially tested using local HTML files and later adapted for live web scraping using the `requests` and `BeautifulSoup` libraries.
3.  **Detailed Information Extraction:** Added functionality to visit the individual detail page for each assessment to extract richer information like descriptions, job levels, duration, languages, and key features.
4.  **Handling Inconsistencies & Edge Cases:** Encountered variations in HTML structure across different pages (especially detail pages) and specific problematic pages (e.g., Page 11 of Pre-packaged solutions). Developed robust parsing logic with multiple selectors, fallbacks, and specific handling for known edge cases.
5.  **Refinement Based on User Feedback:** Iteratively refined the scraper based on specific requirements, such as ensuring detailed descriptions were correctly captured for specific assessments (e.g., "Claims/Operations Supervisor Solution") and eventually applying this detailed fetching logic to *all* assessments, eliminating reliance on generated fallbacks.
6.  **Feature Expansion:** Extended the scraper's capabilities to handle the "Individual Test Solutions" catalog, which involved parameterizing URLs, adjusting pagination logic, and handling differences in table structures between the two catalog types.
7.  **Output Formatting:** Implemented functionality to save the structured data into JSON files and subsequently added a module and command-line options to convert these JSON files into CSV format for easier use in spreadsheet software or databases.
8.  **Testing and Verification:** Regularly tested the scraper against both local files and the live website, verifying the output data (assessment counts, specific field values, file formats) at each major step.

## 3. Core Logic and Components

*   **`shl_scraper/scraper.py` (`Scraper` class):**
    *   Orchestrates the entire scraping process.
    *   Manages fetching HTML content (either from local files via `_get_assessments_from_local` or the live website via `_get_assessments_from_live`).
    *   Handles pagination logic for both "prepack" and "individual" catalogs, constructing appropriate URLs with `type` and `start` parameters.
    *   Includes retry logic (`MAX_RETRIES`) for fetching pages from the live site.
    *   Iterates through basic assessments extracted from catalog pages and calls `_get_detailed_assessment` to fetch and merge detailed information.
    *   Handles the specific Page 11 issue for the pre-packaged catalog by trying an alternative URL.
    *   Saves the final list of assessment dictionaries to separate JSON files based on `catalog_type`.
    *   The `run` method coordinates the scraping for both catalog types.

*   **`shl_scraper/html_parser.py` (`HTMLParser` class):**
    *   Responsible for parsing HTML content using `BeautifulSoup`.
    *   `parse_catalog_page`: Extracts basic assessment information from a catalog list page.
        *   Identifies the main product table, handling potential variations in structure (initially differentiated between prepack/individual tables, later refined to find the most likely table).
        *   Extracts name, URL, `remote_testing` status (green dot check), `adaptive_irt` status (green dot check), and `test_types` from table cells.
    *   `parse_detail_page`: Extracts detailed information from an individual assessment's page.
        *   Uses multiple potential selectors (`h1`, `h2`, `.product-title`, etc.) to find the assessment name.
        *   Employs robust logic to find the description, checking various header tags (`h3`, `h2`, `strong`) and looking for subsequent paragraphs or specific `div` containers. It includes a heuristic check for paragraph length.
        *   Extracts Job Levels, Languages, Key Features, and Test Types by looking for relevant section headers or `div` elements and parsing the content (often lists or paragraphs).
        *   Uses regular expressions (`re.search(r'(\d+)\s*(?:minutes|mins|min)', text, re.IGNORECASE)`) to extract the approximate duration.
        *   Includes helper methods like `_extract_text_after_header`, `_parse_list_or_paragraph`, `_extract_duration`, `_extract_job_levels`, `_generate_key_features`, `_parse_test_types`.

*   **`shl_scraper/json_to_csv.py`:**
    *   Contains the `json_to_csv` function, which takes a JSON file path and CSV file path as input.
    *   Loads the JSON data.
    *   Uses the `csv.DictWriter` to write the data to a CSV file.
    *   Handles list-type fields (e.g., `test_types`, `job_levels`) by joining the elements into a single string separated by "; ".

*   **`shl_scraper/run.py`:**
    *   The main entry point for running the scraper from the command line.
    *   Uses `argparse` to handle command-line arguments (`--convert-csv`, `--csv-only`).
    *   Initializes the `Scraper`.
    *   Calls the `scraper.run()` method unless `--csv-only` is specified.
    *   Optionally calls the `json_to_csv` function from the `json_to_csv` module based on the command-line arguments.

*   **`convert_to_csv.py`:**
    *   A standalone script located at the project root.
    *   Imports and uses the `json_to_csv` function from the `shl_scraper` package.
    *   Provides a simple way to convert existing raw JSON data to processed CSV files without running the full scraper.

## 4. Data Extraction Findings

*   **Data Fields Extracted:** The scraper successfully extracts the following fields for most assessments:
    *   `name`: Assessment title.
    *   `url`: Relative URL to the assessment's detail page.
    *   `remote_testing`: Boolean indicating remote testing availability (from catalog table).
    *   `adaptive_irt`: Boolean indicating adaptive IRT availability (from catalog table).
    *   `test_types`: List of applicable test type categories (e.g., "Ability & Aptitude", "Personality & Behavior").
    *   `description`: Detailed text description from the detail page.
    *   `job_levels`: List of target job levels (e.g., "Entry-Level", "Manager").
    *   `duration`: Approximate completion time (extracted text, often like "Approximate Completion Time in minutes = XX").
    *   `languages`: List of available languages.
    *   `key_features`: List of key assessment features (often derived from test types or specific sections).
    *   `source`: Indicates the origin catalog ("Pre-packaged Job Solutions" or "Individual Test Solutions").
*   **Data Consistency:** While the detail pages provide richer information, the HTML structure varies significantly, requiring complex parsing logic. Data like duration and languages might not always be present or consistently formatted on the detail pages.
*   **Catalog Differences:** The "Pre-packaged Job Solutions" and "Individual Test Solutions" catalogs are presented in structurally similar tables on the initial listing pages, but the detail pages can differ more widely. The number of pages and assessments per page also differs between the two.
*   **Remote/Adaptive Flags:** These boolean flags seem reliably indicated by the presence of green dot icons in the second and third columns of the catalog tables.

## 5. Challenges and Solutions

*   **Inconsistent HTML Structure:** Detail pages lacked a uniform structure for presenting information like description, job levels, duration, etc.
    *   **Solution:** Implemented flexible parsing in `parse_detail_page` using multiple CSS selectors, checking for various tags (`h1`-`h4`, `p`, `div`, `strong`), searching for text patterns (e.g., "Description", "Job Level"), and using heuristics (e.g., minimum paragraph length for description).
*   **Pagination Issues (Page 11):** Page 11 of the pre-packaged solutions sometimes failed to load correctly via the standard URL pattern.
    *   **Solution:** Implemented specific handling in the `Scraper` class (`_get_assessments_from_live`) to try an alternative, known working URL (`https://www.shl.com/shldirect/product-catalog?start=120`) if the initial attempt fails for that specific page.
*   **Differentiating Catalog Tables:** Initially, there was a concern that the tables for pre-packaged and individual solutions might require different parsing logic on the catalog pages.
    *   **Solution:** Parameterized the fetching and parsing methods with `catalog_type`. While initial investigation suggested table differences, the final catalog parsing logic became robust enough to handle both without strict conditional table selection, primarily by looking for a `table` with a reasonable number of `tr` rows.
*   **Ensuring Full Detail Extraction:** Initial versions used fallback/generated descriptions. The requirement shifted to always fetching details from the source page.
    *   **Solution:** Removed fallback generation logic and significantly enhanced `parse_detail_page` to maximize the chances of extracting genuine data from the HTML. Error logging was improved to identify assessments where detail extraction might fail.
*   **List Representation in CSV:** CSV format doesn't natively support lists within cells.
    *   **Solution:** Implemented logic in `json_to_csv` to join list items into a single string using "; " as a delimiter.

## 6. Final Scraper Capabilities

*   Scrapes two distinct SHL assessment catalogs:
    *   Pre-packaged Job Solutions (~141 assessments across 12 pages).
    *   Individual Test Solutions (~377 assessments across 32 pages).
*   Operates using either local HTML files (if available in `data/html/{catalog_type}/page_{n}.html`) or by fetching live data from `shl.com`.
*   Extracts a comprehensive set of attributes for each assessment, prioritizing data from detail pages.
*   Handles website inconsistencies and pagination errors through robust parsing, fallbacks (for Page 11 URL), and retries.
*   Outputs structured data into two separate JSON files:
    *   `data/raw/shl_prepack_assessments.json`
    *   `data/raw/shl_individual_assessments.json`
*   Provides options (via `run.py` arguments or the `convert_to_csv.py` script) to convert the JSON output into CSV format:
    *   `data/processed/shl_prepack_assessments.csv`
    *   `data/processed/shl_individual_assessments.csv`
*   Includes configurable logging for monitoring and debugging.

## 7. Potential Future Improvements

*   **Enhanced Robustness:** Continuously monitor the SHL website for structure changes and update selectors accordingly. Implement more sophisticated fallback logic if detail pages are missing expected sections.
*   **Data Cleaning:** Add post-processing steps to clean extracted data further (e.g., standardize duration format to just the number of minutes, normalize language names).
*   **Configuration File:** Move settings like `MAX_RETRIES`, output paths, and base URLs into a configuration file (`config.yaml` or similar).
*   **Asynchronous Fetching:** For improved performance when scraping live data, implement asynchronous HTTP requests (e.g., using `aiohttp` and `asyncio`).
*   **Delta Updates:** Implement logic to only scrape for new or updated assessments instead of fetching everything each time.
*   **More Sophisticated Error Handling:** Implement more granular error tracking to report exactly which fields failed to extract for specific assessments. 