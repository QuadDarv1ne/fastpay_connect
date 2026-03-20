# Development with PostgreSQL

This guide explains how to set up a PostgreSQL development environment for FastPay Connect.

## Why PostgreSQL for Development?

Using the same database in development and production prevents subtle bugs caused by database-specific behavior differences.

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed
- Git

### Setup

1. **Start the development stack:**

```bash
docker-compose -f docker-compose.dev.yml up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- FastAPI app (port 8080)
- Celery worker
- Celery beat
- Flower monitoring (port 5555)

2. **Run migrations:**

```bash
docker exec -it fastpay-app-dev alembic upgrade head
```

3. **Access the application:**

- API: http://localhost:8080
- Swagger UI: http://localhost:8080/docs
- Flower monitoring: http://localhost:5555

4. **View logs:**

```bash
docker-compose -f docker-compose.dev.yml logs -f app
```

## Connection Details

### PostgreSQL
- Host: localhost
- Port: 5432
- Database: fastpay_connect
- User: fastpay_user
- Password: fastpay_pass
- URL: `postgresql://fastpay_user:fastpay_pass@localhost:5432/fastpay_connect`

### Redis
- Host: localhost
- Port: 6379
- URL: `redis://localhost:6379/0`

## Stopping the Stack

```bash
docker-compose -f docker-compose.dev.yml down
```

To also remove volumes (delete all data):

```bash
docker-compose -f docker-compose.dev.yml down -v
```

## Without Docker

If you prefer not to use Docker:

1. Install PostgreSQL 15+ locally
2. Create database: `CREATE DATABASE fastpay_connect;`
3. Update `alembic.ini`:
   ```ini
   sqlalchemy.url = postgresql://fastpay_user:fastpay_pass@localhost:5432/fastpay_connect
   ```
4. Update `.env`:
   ```env
   DATABASE_URL=postgresql://fastpay_user:fastpay_pass@localhost:5432/fastpay_connect
   REDIS_URL=redis://localhost:6379/0
   ```
5. Run migrations: `alembic upgrade head`

## Testing

Run tests with PostgreSQL:

```bash
# Set test database URL
export TEST_DATABASE_URL=postgresql://fastpay_user:fastpay_pass@localhost:5432/fastpay_connect_test

# Run pytest
pytest
```
