
from ..analysis.anomaly_service import AnomalyDetectionService

if __name__ == "__main__":
    values = [10, 12, 13, 15, 14, 100, 9, 11, 13, 12, 8, 200]
    service = AnomalyDetectionService()
    result = service.detect(values)
    print(result)
