import cv2
import pytesseract
import sys
import re
import json


# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Linux
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows


SENSITIVE_KEYWORDS = ['passport', 'id card', 'SSN', 'ID No.', 'social security']
SENSITIVE_REGEX = [
    r'\d{3}-\d{2}-\d{4}',      # US SSN
    r'\b\d{9}\b',              # 9-digit ID
    r'[A-Z]{2}\d{6,9}',        # Passport-like pattern
    r'[:：]?\s*\d{17}[\dxX]'  
]

def is_sensitive(text):
    for keyword in SENSITIVE_KEYWORDS:
        if keyword.lower() in text.lower():
            return True
    for pattern in SENSITIVE_REGEX:
        if re.search(pattern, text):
            return True
    return False

def run_ocr(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    text = pytesseract.image_to_string(gray, config='--psm 6')
    sensitive = is_sensitive(text)

    result = {
        "sensitive": sensitive,
        "text": text.strip()
    }

    print(json.dumps(result))  

if __name__ == '__main__':
    # if len(sys.argv) < 2:
    #     print(json.dumps({"error": "Missing image path"}))
    # else:
    #     run_ocr(sys.argv[1])
    run_ocr("/ARtest/CapturedImages/frame50.png")