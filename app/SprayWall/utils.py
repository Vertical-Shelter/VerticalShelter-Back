import base64
import io
import requests

from fastapi import UploadFile
from typing import List
from PIL import Image, ImageOps

from .models import Annotations
from ..User.utils import get_user_mini


SVG_TEMPLATE = '''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
    {annotations_svg}
</svg>
'''

async def generate_spraywall_svg(annotations: List[Annotations], image: UploadFile | str) -> str:
    # download image from url
    if isinstance(image, str):
        stream = io.BytesIO(requests.get(image).content)
    else:
        content = await image.read()
        stream = io.BytesIO(content)

    # open image to get width and height (not really efficient but it's fine for now)
    img = Image.open(stream)
    img = ImageOps.exif_transpose(img)
    width, height = img.size

    annotations_svg = ""
    for ann in annotations:
        ann_dict = ann.model_dump()
        points = " ".join(f"{ann_dict['segmentation'][i]},{ann_dict['segmentation'][i + 1]}"
                          for i in range(0, len(ann_dict['segmentation']), 2))
        annotations_svg += f'<path id="{ann_dict["id"]}" class="hold" d="M {points} Z" />\n'

    svg = SVG_TEMPLATE.format(
        width=width,
        height=height,
        annotations_svg=annotations_svg,
    )

    return svg


def sentwalls_ref_to_uids(sentwalls):
    # users/uid/sentwalls/sentwall_id -> uid
    return [sentwall.parent.parent.id for sentwall in sentwalls]


async def get_likes(like_ref):
    like_dict = like_ref.to_dict()
    like_dict["id"] = like_ref.id
    like_dict["date"] = like_dict["date"].strftime("%Y-%m-%d %H:%M:%S")
    like_dict["user"] = await get_user_mini(like_dict.get("user"))
    return like_dict


async def get_comments(comment_ref):
    comment_dict = comment_ref.to_dict()
    comment_dict["id"] = comment_ref.id
    comment_dict["date"] = comment_dict["date"].strftime("%Y-%m-%d %H:%M:%S")
    comment_dict["user"] = await get_user_mini(comment_dict.get("user"))
    return comment_dict
