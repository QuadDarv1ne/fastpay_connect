# Procfile для Heroku, Railway и других платформ
# Документация: https://devcenter.heroku.com/articles/procfile

# Web сервер
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2

# Worker для фоновых задач (опционально)
worker: python -m celery -A app.tasks.celery worker --loglevel=info

# Миграции БД (запускать вручную или через release)
release: alembic upgrade head

# Health check
health: curl -f http://localhost:$PORT/health || exit 1
