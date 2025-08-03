Data Extraction API Service

Django REST API service for data extraction with robust testing capabilities. This service provides endpoints for managing data extraction jobs from third-party services, with full support for asynchronous processing, job status tracking, and result retrieval.

Features

- **Asynchronous Data Extraction**: Start, monitor, and manage extraction jobs
- **Job Status Tracking**: Real-time status updates for pending, in-progress, completed, failed, and cancelled jobs
- **Paginated Results**: Efficient handling of large datasets with pagination support
- **Comprehensive API**: Full CRUD operations for extraction jobs
- **Robust Testing**: Comprehensive test suite covering seeded data, real extraction, and edge cases
- **Health Monitoring**: Built-in health check endpoint
- **Statistics**: Aggregated statistics about extraction jobs

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run Database Migrations

```bash
python manage.py migrate
```

### 3. Seed Test Data (Optional)

```bash
python manage.py seed_test_data --clear
```

### 4. Start the Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/v1/`