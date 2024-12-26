from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.routes.payment_routes import router as payment_router
from app.routes.webhook_routes import router as webhook_router

# Инициализация логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Добавление поддержки CORS
origins = ["http://localhost", "https://yourfrontend.com"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Укажите разрешенные источники
    allow_credentials=True,  # Разрешение на использование cookies
    allow_methods=["*"],  # Разрешенные HTTP методы
    allow_headers=["*"],  # Разрешенные заголовки
)

# Указываем путь к шаблонам
templates = Jinja2Templates(directory="app/templates")

# Подключаем статические файлы
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключаем маршруты
app.include_router(payment_router, prefix="/payments", tags=["payments"])
app.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])

# Главная страница с шаблоном
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Рендерит главную страницу приложения с использованием шаблона.

    :param request: Объект запроса.
    :return: HTML-страница с главной страницей приложения.
    """
    try:
        logger.info("Rendering home page")
        return templates.TemplateResponse("home.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering home page: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Пример обработки ошибок
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """
    Обработчик непредвиденных ошибок в приложении.

    :param request: Объект запроса.
    :param exc: Исключение, которое было вызвано.
    :return: Ответ с ошибкой 500 (Внутренняя ошибка сервера).
    """
    logger.error(f"Unhandled error: {exc}")
    return HTMLResponse(status_code=500, content="Something went wrong, please try again later.")
