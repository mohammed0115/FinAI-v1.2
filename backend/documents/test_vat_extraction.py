
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ocr_service import DocumentOCRService

if __name__ == "__main__":
    service = DocumentOCRService()
    text = "فاتورة رقم: 12345\nVAT: 31234567890123\nالإجمالي: 1000.00\nالضريبة: 150.00"
    result = service.extract_structured_data(text, "invoice")
    print(result)
