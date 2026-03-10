# Makefile для автоматизации деплоя и разработки
# Использование: make <command>

.PHONY: help install dev test build docker-up docker-down deploy-k8s deploy-render deploy-railway

# Переменные
IMAGE_NAME := fastpay/fastpay-connect
IMAGE_TAG := latest
DOCKER_COMPOSE := docker-compose
KUBECTL := kubectl
NAMESPACE := fastpay

# Цвета
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Установка зависимостей
	@echo "$(GREEN)Установка зависимостей...$(NC)"
	pip install -r requirements.txt
	pip install -r requirements-dev.txt 2>/dev/null || true

dev: ## Запуск в режиме разработки
	@echo "$(GREEN)Запуск в режиме разработки...$(NC)"
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8080

test: ## Запуск тестов
	@echo "$(GREEN)Запуск тестов...$(NC)"
	pytest tests/ -v --cov=app --cov-report=html

test-fast: ## Быстрый запуск тестов без coverage
	pytest tests/ -v

lint: ## Проверка кода линтером
	flake8 app/ tests/
	pylint app/

format: ## Форматирование кода
	black app/ tests/
	isort app/ tests/

docker-build: ## Сборка Docker образа
	@echo "$(GREEN)Сборка Docker образа...$(NC)"
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

docker-up: ## Запуск Docker Compose (production)
	@echo "$(GREEN)Запуск Docker Compose...$(NC)"
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml up -d

docker-down: ## Остановка Docker Compose
	@echo "$(GREEN)Остановка Docker Compose...$(NC)"
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml down

docker-logs: ## Просмотр логов Docker
	docker-compose -f docker-compose.prod.yml logs -f

docker-restart: ## Перезапуск Docker Compose
	@echo "$(GREEN)Перезапуск Docker Compose...$(NC)"
	$(DOCKER_COMPOSE) -f docker-compose.prod.yml restart

migrate: ## Запуск миграций Alembic
	@echo "$(GREEN)Запуск миграций...$(NC)"
	alembic upgrade head

migrate-revision: ## Создание новой миграции
	@echo "$(GREEN)Создание новой миграции...$(NC)"
	alembic revision --autogenerate -m "$(MESSAGE)"

db-init: ## Инициализация базы данных
	@echo "$(GREEN)Инициализация базы данных...$(NC)"
	python -c "from app.database import Base, engine; Base.metadata.create_all(engine)"

deploy-render: ## Деплой на Render
	@echo "$(GREEN)Деплой на Render...$(NC)"
	@echo "Перейдите на https://render.com и подключите репозиторий"
	@echo "Или используйте CLI: renderctl deploy fastpay-connect"

deploy-railway: ## Деплой на Railway
	@echo "$(GREEN)Деплой на Railway...$(NC)"
	@echo "Установите Railway CLI: npm install -g @railway/cli"
	@echo "Затем выполните: railway login && railway up"

deploy-flyio: ## Деплой на Fly.io
	@echo "$(GREEN)Деплой на Fly.io...$(NC)"
	flyctl auth login
	flyctl deploy --config fly.toml

deploy-k8s: ## Деплой на Kubernetes
	@echo "$(GREEN)Деплой на Kubernetes...$(NC)"
	$(KUBECTL) apply -f k8s/deployment.yaml
	$(KUBECTL) rollout status deployment/fastpay-app -n $(NAMESPACE)

deploy-k8s-rollback: ## Откат деплоя Kubernetes
	@echo "$(GREEN)Откат деплоя Kubernetes...$(NC)"
	$(KUBECTL) rollout undo deployment/fastpay-app -n $(NAMESPACE)

k8s-logs: ## Просмотр логов в Kubernetes
	$(KUBECTL) logs -n $(NAMESPACE) -l app=fastpay -f

k8s-scale: ## Масштабирование приложения в Kubernetes
	$(KUBECTL) scale deployment fastpay-app --replicas=$(REPLICAS) -n $(NAMESPACE)

heroku-deploy: ## Деплой на Heroku
	@echo "$(GREEN)Деплой на Heroku...$(NC)"
	git push heroku main
	heroku run alembic upgrade head

gcp-deploy: ## Деплой на Google Cloud Run
	@echo "$(GREEN)Деплой на Google Cloud Run...$(NC)"
	gcloud builds submit --tag gcr.io/$$(gcloud config get-value project)/fastpay-connect
	gcloud run deploy fastpay-connect \
		--image gcr.io/$$(gcloud config get-value project)/fastpay-connect \
		--platform managed \
		--region us-central1 \
		--allow-unauthenticated

aws-deploy: ## Деплой на AWS Elastic Beanstalk
	@echo "$(GREEN)Деплой на AWS Elastic Beanstalk...$(NC)"
	eb deploy

health: ## Проверка здоровья приложения
	@echo "$(GREEN)Проверка здоровья...$(NC)"
	curl -f http://localhost:8080/health || echo "❌ Health check failed"

logs: ## Просмотр логов приложения
	tail -f logs/app.log

logs-error: ## Просмотр только ошибок
	tail -f logs/error.log

clean: ## Очистка временных файлов
	@echo "$(GREEN)Очистка временных файлов...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info

clean-docker: ## Очистка Docker ресурсов
	@echo "$(GREEN)Очистка Docker ресурсов...$(NC)"
	docker system prune -af
	docker volume prune -f

backup: ## Создание резервной копии БД
	@echo "$(GREEN)Создание резервной копии БД...$(NC)"
	@mkdir -p backups
	docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U fastpay_user fastpay_connect > backups/backup_$$(date +%Y%m%d_%H%M%S).sql

restore: ## Восстановление БД из резервной копии
	@echo "$(GREEN)Восстановление БД из резервной копии...$(NC)"
	@echo "Использование: make restore FILE=backups/backup_20240101_120000.sql"
	@[ -f $(FILE) ] || (echo "❌ Файл не найден: $(FILE)" && exit 1)
	docker-compose -f docker-compose.prod.yml exec -T db psql -U fastpay_user fastpay_connect < $(FILE)

ci: ## Запуск CI проверок
	@echo "$(GREEN)Запуск CI проверок...$(NC)"
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) docker-build

prod: ## Деплой на production
	@echo "$(GREEN)Деплой на production...$(NC)"
	$(MAKE) docker-build
	$(MAKE) docker-up
	$(MAKE) health
