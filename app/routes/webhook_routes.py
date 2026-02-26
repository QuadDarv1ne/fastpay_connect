from fastapi import APIRouter, HTTPException, Request, Depends
from app.payment_gateways.yookassa import handle_yookassa_webhook
from app.payment_gateways.tinkoff import handle_tinkoff_webhook
from app.payment_gateways.cloudpayments import handle_cloudpayments_webhook
from app.payment_gateways.unitpay import handle_unitpay_webhook
from app.payment_gateways.robokassa import handle_robokassa_webhook
from app.database import get_db
from app.services.payment_service import update_payment_status
from sqlalchemy.orm import Session

router = APIRouter()


async def process_webhook(payment_system: str, payload: dict, signature: str, db: Session) -> dict:
    """
    Общая функция для обработки webhook уведомлений.
    """
    try:
        result = None
        if payment_system == "yookassa":
            result = await handle_yookassa_webhook(payload, signature)
        elif payment_system == "tinkoff":
            result = await handle_tinkoff_webhook(payload, signature)
        elif payment_system == "cloudpayments":
            result = await handle_cloudpayments_webhook(payload, signature)
        elif payment_system == "unitpay":
            result = await handle_unitpay_webhook(payload, signature)
        elif payment_system == "robokassa":
            result = await handle_robokassa_webhook(payload, signature)
        else:
            raise HTTPException(status_code=400, detail="Unknown payment system")
        
        # Обновляем статус в БД
        order_id = payload.get("order_id") or payload.get("payment_id")
        status_map = {
            "payment successful": "completed",
            "payment canceled": "cancelled",
            "payment failed": "failed",
        }
        db_status = status_map.get(result.get("message", "").lower(), "pending")
        
        if order_id and result.get("status") == "processed":
            update_payment_status(
                db=db,
                order_id=order_id,
                status=db_status,
                metadata=payload
            )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing webhook: {str(e)}")


@router.post("/yookassa")
async def yookassa_webhook(request: Request, db: Session = Depends(get_db)):
    """Обрабатывает webhook уведомления от YooKassa."""
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("yookassa", payload, signature, db)
    return {"status": "success", "message": result}


@router.post("/tinkoff")
async def tinkoff_webhook(request: Request, db: Session = Depends(get_db)):
    """Обрабатывает webhook уведомления от Tinkoff."""
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("tinkoff", payload, signature, db)
    return {"status": "success", "message": result}


@router.post("/cloudpayments")
async def cloudpayments_webhook(request: Request, db: Session = Depends(get_db)):
    """Обрабатывает webhook уведомления от CloudPayments."""
    payload = await request.json()
    token = payload.get("token", request.headers.get("X-Signature", ""))
    result = await process_webhook("cloudpayments", payload, token, db)
    return {"status": "success", "message": result}


@router.post("/unitpay")
async def unitpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Обрабатывает webhook уведомления от UnitPay."""
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("unitpay", payload, signature, db)
    return {"status": "success", "message": result}


@router.post("/robokassa")
async def robokassa_webhook(request: Request, db: Session = Depends(get_db)):
    """Обрабатывает webhook уведомления от Робокасса."""
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("robokassa", payload, signature, db)
    return {"status": "success", "message": result}
