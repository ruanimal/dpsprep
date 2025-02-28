from typing import Literal

from loguru import logger
from PIL import Image, ImageOps
import djvu.decode
import djvu.sexpr


ImageMode = Literal['rgb', 'bitonal']


djvu_pixel_formats = {
    'rgb': djvu.decode.PixelFormatRgb(byte_order='RGB'),
    'bitonal': djvu.decode.PixelFormatPackedBits('>'),
}


for pixel_format in djvu_pixel_formats.values():
    pixel_format.rows_top_to_bottom = 1
    pixel_format.y_top_to_bottom = 0


pil_modes = {
    'rgb': 'RGB',
    'bitonal': '1',
}


def djvu_page_to_image(page: djvu.decode.Page, i: int) -> Image.Image:
    page_job = page.decode(wait=True)
    width, height = page_job.size
    buffer = bytearray(3 * width * height) # RGB at most

    rect = (0, 0, width, height)
    mode = 'bitonal' if page_job.type == djvu.decode.PAGE_TYPE_BITONAL else 'rgb'

    if mode == 'bitonal':
        if not hasattr(Image.core, 'libtiff_encoder'):  # type: ignore
            logger.warning('Bitonal image compression may suffer because Pillow has been built without libtiff support.')
    else:
        if not hasattr(Image.core, 'libjpeg_encoder'):  # type: ignore
            logger.warning('Multitonal image compression may suffer because Pillow has been built without libjpeg support.')

    try:
        page_job.render(
            # RENDER_COLOR is simply a default value and doesn't actually imply colors
            mode=djvu.decode.RENDER_COLOR,
            page_rect=rect,
            render_rect=rect,
            pixel_format=djvu_pixel_formats[mode],
            buffer=buffer
        )
    except djvu.decode.NotAvailable:
        logger.warning(f'libdjvu claims that data for page {i + 1} is not available. Returning a blank page instead.')
        image = Image.new(
            pil_modes['bitonal'],
            page_job.size
        )
    else:
        image = Image.frombuffer(
            pil_modes[mode],
            page_job.size,
            buffer,
            'raw'
        )

    # I have experimentally determined that we need to invert the images. -- Ianis, 2023-05-13
    return ImageOps.invert(image)
