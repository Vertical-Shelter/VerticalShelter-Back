from fastapi.responses import FileResponse, HTMLResponse
from .settings import app
from .metrics import QRCODE_COUNTER
from fastapi import Request

# Set up Jinja2 template directory
@app.get("/app/{full_path:path}", response_class=HTMLResponse)
async def universal_link_fallback(request: Request, full_path: str):
    """
    Endpoint to handle the fallback for Universal Links.
    Tries to open the app and redirects to the App Store if it’s not installed.
    """
    # print("request", request)
    # print("full_path", full_path)

    params = request.query_params
    cloc_id = params.get("climbingLocationId")
    qrcodeType = full_path

    print(cloc_id, qrcodeType)

    if cloc_id:
        # Register the qrcode request
        QRCODE_COUNTER.labels(
            climbingLocation_id=cloc_id,
            qrcode_type=qrcodeType,
        ).inc()

    # Render the HTML template and pass the news ID dynamically if needed
    return FileResponse("static/universal_link_fallback.html")
