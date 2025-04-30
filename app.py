import os
from flask import Flask, request, render_template
from werkzeug.utils import secure_filename
import pytesseract
from PIL import Image
import cv2
from pdf2image import convert_from_path
import re
import numpy as np

# Optional HEIC support
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    print("HEIC support not available. Install with: pip install pillow-heif")

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def convert_pdf_to_image(pdf_path):
    images = convert_from_path(pdf_path)
    jpg_path = pdf_path + ".jpg"
    images[0].save(jpg_path, "JPEG")  # Use first page only
    return jpg_path

def extract_text(image_path):
    try:
        # Try reading using OpenCV
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError("OpenCV failed to read image.")

    except Exception:
        # Fallback: read with Pillow
        try:
            with Image.open(image_path) as pil_img:
                pil_img = pil_img.convert("RGB")  # this avoids .mode error
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"[ERROR] Failed to process image: {e}")
            return []

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    return text.split('\n')

def guess_product_lines(lines):
    candidates = []
    for line in lines:
        match = re.search(r'^(.*?)(\d{1,2}\.\d{2})(?!\S)', line.strip())  # matches X.XX or XX.XX at end
        if match:
            before_price = match.group(1).strip()
            if len(before_price) > 3 and not any(k in before_price.lower() for k in ['total', 'tax', 'subtotal', 'change', 'amount', 'approved', 'visa', 'member']):
                candidates.append(before_price)
    return candidates

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['receipt']
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        # Convert PDF to image if needed
        if filename.lower().endswith('.pdf'):
            path = convert_pdf_to_image(path)

        lines = extract_text(path)
        product_lines = guess_product_lines(lines)
        return render_template('index.html', product_lines=product_lines, raw_text=lines)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
