-- Инициализация базы данных PostgreSQL
-- Этот скрипт выполняется при первом запуске контейнера

-- Создание расширений
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Создание пользователя (если не создан)
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = 'fastpay_user') THEN
      CREATE ROLE fastpay_user LOGIN PASSWORD 'change_me_in_production';
   END IF;
END
$do$;

-- Создание базы данных (если не создана)
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_database WHERE datname = 'fastpay_connect') THEN
      CREATE DATABASE fastpay_connect OWNER fastpay_user;
   END IF;
END
$do$;

-- Предоставление прав
GRANT ALL PRIVILEGES ON DATABASE fastpay_connect TO fastpay_user;

-- Подключение к базе данных
\c fastpay_connect;

-- Создание схемы
CREATE SCHEMA IF NOT EXISTS app;
GRANT ALL ON SCHEMA app TO fastpay_user;

-- Настройка pooler (опционально для PgBouncer)
-- ALTER SYSTEM SET max_connections = 200;
-- ALTER SYSTEM SET shared_buffers = 256MB;
