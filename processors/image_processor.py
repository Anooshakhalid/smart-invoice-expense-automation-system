# processors/image_processor.py

import pytesseract
from PIL import Image

def extract_text_from_image(path):
    return pytesseract.image_to_string(Image.open(path))