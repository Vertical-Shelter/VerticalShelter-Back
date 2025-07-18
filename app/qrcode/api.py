from fastapi import Depends, Body, HTTPException
from fastapi.responses import FileResponse, StreamingResponse, Response
import base64

from ..User.deps import get_current_user
from ..settings import firestore_async_db, app
from ..metrics import QRCODE_COUNTER
from .utils import create_custom_qrcode_png, create_custom_qrcode_artistic

QRCODE_APP_BASE_URL = "XXXXXX"  # Replace with the actual base URL for your QR code application

@app.post("/api/v1/qrcode/generate/{vt_type}")
async def generate_qrcode(
    vt_type: str,
    body: dict = Body(None),
    artistic: bool = False,
    # uid: str = Depends(get_current_user),
):
    if body is None:
        raise HTTPException(status_code=400, detail="Body is required")

    # add params to base url
    qrcode_url = f"{QRCODE_APP_BASE_URL}{vt_type}?"
    num_params = len(body)
    for i in range(0, num_params):
        key, value = list(body.items())[i]
        if i == num_params - 1:
            qrcode_url = f"{qrcode_url}{key}={value}"
        else:
            qrcode_url = f"{qrcode_url}{key}={value}&"

    # create qrcode
    if artistic:
        out = create_custom_qrcode_artistic(qrcode_url)
    else:
        out = create_custom_qrcode_png(qrcode_url)

    return StreamingResponse(out, media_type="image/png")

@app.get("/api/v1/qrcode/generate/climbingLocation/{climbingLocation_id}")
async def generate_qrcode_climbingLocation(
    climbingLocation_id: str,
    artistic: bool = False,
    # uid: str = Depends(get_current_user),
):
    climbingLocation = await firestore_async_db.collection("climbingLocations").document(climbingLocation_id).get()
    climbingLocation_dict = climbingLocation.to_dict()
    if not climbingLocation.exists:
        raise HTTPException(status_code=404, detail="ClimbingLocation not found")
    
    gym_name = climbingLocation_dict.get("name") + " - " + climbingLocation_dict.get("city")
    
    # generate qrcode for all sectors
    secteurs = climbingLocation.reference.collection("secteurs").stream()

    res_html = ""
    res_html += f"<div style='display: grid; grid-template-columns: repeat(3, 1fr); grid-gap: 20px;'>"

    async for secteur in secteurs:
        secteur_label = secteur.to_dict().get('newlabel')
        if not secteur_label:
            continue

        qrcode_url = f"{QRCODE_APP_BASE_URL}vt_main_page?climbingLocationId={climbingLocation_id}&secteurName={secteur_label}"

        if artistic:
            out = create_custom_qrcode_artistic(qrcode_url)
        else:
            out = create_custom_qrcode_png(qrcode_url)

        img_base64 = base64.b64encode(out.getvalue()).decode("utf-8")

        res_html += f"<div>"
        res_html += f"<h2>{secteur_label}</h2>"
        res_html += f"<img src='data:image/png;base64,{img_base64}' />"
        res_html += f"</div>"


    html_content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>QR Codes for {gym_name}</title>
        </head>
        <body>
            <h1>QR Codes for {gym_name}</h1>
            {res_html}
        </body>
    </html>
    """

    return Response(content=html_content, media_type="text/html")