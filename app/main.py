from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from pathlib import Path
from app.routes.payment_routes import router as payment_router
from app.routes.webhook_routes import router as webhook_router

app = FastAPI()

# Указываем путь к папке с шаблонами
templates = Jinja2Templates(directory="app/templates")

# Подключите путь к статическим файлам
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Подключение маршрутов
app.include_router(payment_router, prefix="/payments", tags=["payments"])
app.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])

# Главная страница с шаблоном
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})
