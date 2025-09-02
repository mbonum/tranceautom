# Tranche Automation - Django Application

TODO: Estrarre date colonna -

## Overview

Tranche Automation is a Django web application designed to process Excel planning files containing product data and country-specific information. The application extracts, validates, and transforms this data into XML format for integration with PIM (Product Information Management) systems.

## Project Architecture

The application follows a modular architecture with clear separation of concerns:

### Core Components

- **Models** (`upload_file/models.py`): Database models for planning imports, products, and country planning
- **Views** (`upload_file/views.py`): HTTP request handlers and user interface logic
- **Processors** (`upload_file/processors.py`): Business logic for data processing and validation
- **Parsers** (`upload_file/parsers.py`): Excel file parsing and header extraction
- **XML Generator** (`upload_file/xml_generator.py`): XML export functionality
- **Country Processors** (`upload_file/correct_country_processor.py`, `upload_file/simple_country_processor.py`): Country-specific data extraction

## Data Pipeline

### 1. File Upload and Validation
- **Function**: `handle_file_upload()` in `views.py`
- **Purpose**: Accepts Excel files and validates their structure
- **Validation**: Checks for required "PIANIFICAZIONE" sheet and specific column headers
- **Output**: Creates `PianificazioneImport` record

### 2. Excel Parsing and Header Extraction
- **Function**: `ExcelHeaderParser` in `parsers.py`
- **Purpose**: Extracts and validates Excel headers
- **Process**: 
  - Identifies header row containing country groups
  - Maps column positions to product fields
  - Validates required columns (codice_forn, commerce, made_in, etc.)

### 3. Product Data Processing
- **Function**: `ProductDataProcessor` in `processors.py`
- **Purpose**: Processes individual product rows
- **Steps**:
  - Extracts product data using predefined column mappings
  - Validates product information
  - Applies business rules and transformations
  - Creates `Prodotto` instances

### 4. Country Planning Extraction
- **Function**: `CorrectCountryPlanningProcessor` in `correct_country_processor.py`
- **Purpose**: Extracts country-specific planning data
- **Process**:
  - Identifies country groups in headers (e.g., "IT/ES/FR")
  - Extracts dates and quantities for each country
  - Handles complex date formats and country combinations

### 5. Data Validation and Storage
- **Function**: `ValidationProcessor` in `processors.py`
- **Purpose**: Validates processed data before database storage
- **Checks**: Product completeness, country data validity, date formats

### 6. XML Generation
- **Function**: `XMLExportManager` in `xml_generator.py`
- **Purpose**: Generates XML output for PIM integration
- **Features**:
  - Full planning export
  - Tranche-specific export
  - Optimized XML structure

## Key Functions and Their Purposes

### Authentication Views
- `user_login()`: User authentication
- `user_logout()`: User logout
- `user_register()`: User registration

### Main Application Views
- `home()`: Main dashboard with file upload
- `handle_file_upload()`: File processing orchestration
- `planning_details()`: Display processed data
- `download_xml()`: XML generation and download

### Data Processing Functions
- `_process_excel_file()`: Main processing pipeline
- `_extract_product_data()`: Product information extraction
- `_apply_business_rules()`: Business logic application
- `process_csv_file()`: CSV processing for country data

## Country Extraction Issues and Challenges

### 1. Complex Header Structure
**Problem**: Excel files contain complex header structures with country groups and date ranges.

**Example**:
```
Header: "IT/ES/FR 01/01/2024-31/03/2024"
```

**Solution**: 
- `CorrectCountryPlanningProcessor` uses regex patterns to identify country groups
- Implements `_find_header_row_with_countries()` to locate the correct header row
- Maps country codes to standardized format

### 2. Date Format Variations
**Problem**: Multiple date formats across different files and countries.

**Formats encountered**:
- DD/MM/YYYY
- MM/DD/YYYY
- YYYY-MM-DD
- Date ranges: "01/01/2024-31/03/2024"

**Solution**:
- `DateNormalizer` class standardizes date formats
- `TrancheDateConverter` handles date range parsing
- Validation ensures consistent date handling

### 3. Country Code Mapping
**Problem**: Inconsistent country code representations and missing countries.

**Issues**:
- Some countries missing from standard lists
- Mixed country code formats (2-letter vs 3-letter)
- Special cases like "XK" (Kosovo)

**Solution**:
- Comprehensive country list in `ALL_COUNTRIES`
- Country validation and normalization
- Error handling for unknown countries

### 4. Data Quality Issues
**Problem**: Inconsistent data quality in source Excel files.

**Common Issues**:
- Empty cells in critical columns
- Mixed data types in same column
- Encoding problems with special characters
- Inconsistent row structures

**Solution**:
- Robust data validation in `ValidationProcessor`
- Pre-processing in `_preprocess_csv()`
- Error logging and user feedback

### 5. Performance with Large Files
**Problem**: Processing large Excel files with thousands of products and countries.

**Challenges**:
- Memory usage with large datasets
- Processing time for complex country extractions
- Database transaction management

**Solution**:
- Batch processing in `ProductDataProcessor`
- Database transactions for data integrity
- Progress tracking and user feedback

## Database Models

### PianificazioneImport
- Tracks file imports and processing status
- Stores metadata about the import process
- Links to user who performed the import

### Prodotto
- Stores individual product information
- Links to planning import
- Contains raw data for reference

### PaesePianificazione
- Stores country-specific planning data
- Links products to countries and dates
- Contains quantity and date information

## Setup and Installation

## Local Development Setup

There are two ways to set up the database for local development. Using a local Docker container is the recommended approach as it does not depend on network connectivity to GCP.

### Option 1: Local PostgreSQL with Docker (Recommended)

1.  Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2.  Create a `.env` file from the example: `copy .env.example .env`.
3.  In the `.env` file, ensure the `DATABASE_URL` for the local Docker database is uncommented and set a password.
4.  In a terminal, start the database container: `docker-compose up -d`.
5.  You can now run the Django application locally.

### Option 2: Connecting to Cloud SQL (Requires Network Access)

### Prerequisites
1.  **Connect to the company VPN**: Your network administrator must ensure you have a route from your machine to the project's VPC network.
2.  **Authenticate with gcloud**: Run `gcloud auth application-default login`.
3.  **Create a `.env` file**: Copy `.env.example` to `.env` and fill in the secrets for local development. Uncomment the `DATABASE_URL` for Cloud SQL and use the real password.

### Running the Application
1.  If connecting to Cloud SQL, start the Cloud SQL Auth Proxy in a dedicated terminal.
    ```bash
    cloud-sql-proxy.exe --port 5432 --private-ip clz-tmp-innovation-dev:europe-west3:tranche-autom-db
    ```
2.  In a second terminal, activate your virtual environment and run the Django commands.
    ```bash
    uv run python manage.py migrate
    uv run python manage.py runserver
    ```

### Troubleshooting Cloud SQL Connection
If the Cloud SQL Auth Proxy fails to connect, your machine likely cannot reach the database's private IP. Contact your cloud infrastructure or network team for assistance. You can test connectivity with PowerShell: `Test-NetConnection <DB_PRIVATE_IP> -Port 3307`.

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Database setup
python manage.py migrate
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## Usage

1. **Upload Excel File**: Navigate to home page and upload planning Excel file
2. **Validation**: System validates file structure and extracts data
3. **Review**: View processed data in planning details page
4. **Export**: Generate and download XML for PIM integration
5. **Upload to PIM**: Manually upload XML to PIM folder

## Technical Requirements

- Python 3.12+
- Django 4.2+
- pandas for Excel processing
- XML generation capabilities
- SQLite/PostgreSQL database

## Future Improvements

- Enhanced country extraction algorithms
- Better error handling and user feedback
- Performance optimization for large files
- Integration with PIM APIs
- Advanced validation rules
