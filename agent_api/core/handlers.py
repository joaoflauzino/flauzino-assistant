from fastapi import Request
from fastapi.responses import JSONResponse

async def finance_unreachable_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=503,
        content={"message": "Service unavailable", "detail": str(exc)},
    )


async def invalid_spent_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=400,
        content={"message": "Invalid data", "detail": str(exc)},
    )


async def finance_server_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=502,
        content={"message": "Upstream error", "detail": str(exc)},
    )


async def llm_provider_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=503,
        content={"message": "AI Service Temporarily Unavailable", "detail": str(exc)},
    )


async def service_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )


async def ocr_processing_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=400,
        content={"message": "OCR Processing Error", "detail": str(exc)},
    )


async def invalid_image_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=400,
        content={"message": "Invalid Image", "detail": str(exc)},
    )


async def audio_processing_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=400,
        content={"message": "Audio Processing Error", "detail": str(exc)},
    )


async def invalid_audio_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=400,
        content={"message": "Invalid Audio", "detail": str(exc)},
    )
