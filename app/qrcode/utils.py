import segno
import os
import io
from PIL import Image

from ..settings import storage_client, BUCKET_NAME

file_dir = os.path.dirname(__file__)
center_logo_path = os.path.join(file_dir, "VS.png")

def create_custom_qrcode_png(qrcode_url, bucket_url=None):
    qr = segno.make(qrcode_url, error='h')
    out = io.BytesIO()
    qr.save(out, scale=10, kind="png", dark="#210124", border=1)
    out.seek(0)

    qr_img = Image.open(out)
    qr_img = qr_img.convert("RGBA")
    qrcode_size = qr_img.size[0]

    center_logo_size = qrcode_size // 4

    center_logo = Image.open(center_logo_path)
    center_logo = center_logo.convert("RGBA")
    center_logo = center_logo.resize((center_logo_size, center_logo_size))

    center = (qrcode_size - center_logo_size) // 2
    qr_img.paste(center_logo, (center, center), center_logo)

    # upload qrcode image to bucket 

    out = io.BytesIO()
    qr_img.save(out, format="PNG")
    out.seek(0)
    if bucket_url:
        blob = storage_client.bucket(BUCKET_NAME).blob(bucket_url)
        blob.upload_from_file(out, content_type="image/png")
        return blob.public_url
    
    return out

def create_custom_qrcode_artistic(qrcode_url, bucket_url=None):
    qr = segno.make(qrcode_url, error='h')
    out = io.BytesIO()
    qr.to_artistic(background=center_logo_path, target=out, scale=10, kind="png", dark="#210124", border=1)
    out.seek(0)

    qr_img = Image.open(out)

    # upload qrcode image to bucket 
    if bucket_url:
        blob = storage_client.bucket(BUCKET_NAME).blob(bucket_url)
        blob.upload_from_string(qr_img.tobytes(), content_type="image/png")
        return blob.public_url

    out = io.BytesIO()
    qr_img.save(out, format="PNG")
    out.seek(0)
    return out
