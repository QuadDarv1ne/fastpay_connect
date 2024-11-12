from fastapi import FastAPI
from app.routes.payment_routes import router as payment_router
from app.routes.webhook_routes import router as webhook_router

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Подключение маршрутов
app.include_router(payment_router, prefix="/payments", tags=["payments"])
app.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])

# Главная страница
@app.get("/", response_class=HTMLResponse)
async def root():
    return {"message": "Welcome to the FastPay Connect API"}

async def read_home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


