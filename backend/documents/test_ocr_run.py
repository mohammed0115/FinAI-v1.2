
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ocr_service import DocumentOCRService

def test_ocr_image():
    # ضع هنا مسار صورة اختبارية موجودة لديك
    test_image_path = os.path.join(os.path.dirname(__file__), 'test_image.png')
    if not os.path.exists(test_image_path):
        print('Test image not found:', test_image_path)
        return
    ocr_service = DocumentOCRService()
    result = ocr_service.process_document(
        file_path=test_image_path,
        file_type='.png',
        language='mixed',
        is_handwritten=False
    )
    print('OCR Result:', result)

if __name__ == '__main__':
    test_ocr_image()
