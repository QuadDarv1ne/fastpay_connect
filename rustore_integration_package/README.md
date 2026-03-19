# RuStore Pay SDK Integration Package

Пакет для интеграции RuStore Pay SDK в проект fastpay_connect.

## Содержимое пакета

```
rustore_integration_package/
├── README.md                           # Этот файл
├── INSTALL.md                          # Инструкция по установке
├── app/
│   └── payment_gateways/
│       └── rustore.py                  # Серверный gateway для RuStore
├── docs/
│   ├── RuStore_Pay_SDK_Guide.docx      # Подробный гайд (Word)
│   └── rustore_integration.md          # Документация по интеграции
├── examples/
│   └── android/
│       ├── RuStorePaymentManager.kt    # Android менеджер платежей
│       └── FastPayApiClient.kt         # API клиент для валидации
└── tests/
    └── test_rustore.py                 # Unit-тесты
```

## Быстрая установка

### 1. Серверная часть

```bash
# Копируем gateway
cp app/payment_gateways/rustore.py /path/to/fastpay_connect/app/payment_gateways/

# Копируем тесты
cp tests/test_rustore.py /path/to/fastpay_connect/tests/
```

### 2. Настройки (.env)

```env
# RuStore Pay SDK
RUSTORE_CONSOLE_APPLICATION_ID=your_console_app_id
RUSTORE_API_KEY=your_api_key
RUSTORE_SECRET_KEY=your_secret_key
RUSTORE_RETURN_URL=https://your-domain.com/payment/return
```

### 3. Android интеграция

Скопируйте файлы из `examples/android/` в ваш Android проект.

## Документация

- **docs/RuStore_Pay_SDK_Guide.docx** — подробный гайд по Pay SDK (Word, 16pt заголовки, 14pt текст)
- **docs/rustore_integration.md** — полная документация по интеграции

## Форматирование документа

Документ `RuStore_Pay_SDK_Guide.docx` создан с параметрами:
- Шрифт: Times New Roman
- Межстрочный интервал: 1.5
- Отступ первой строки: 1.25 см
- Заголовки: 16pt
- Подзаголовки: 14pt
- Основной текст: 14pt

## Требования

- Python 3.10+
- FastAPI 0.100+
- httpx
- Android: Kotlin, RuStore Pay SDK 10.x

## Поддержка

- RuStore: support@rustore.ru (тема: "Pay SDK")
- Проект: https://github.com/QuadDarv1ne/fastpay_connect/issues
