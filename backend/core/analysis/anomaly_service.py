class AnomalyDetectionService:
    """
    كشف الشذوذ بطريقة إحصائية (IQR)
    لا يستخدم أي AI أو ML تسويقي
    """
    @staticmethod
    def detect_outliers_iqr(values):
        if not values:
            return []
        values = sorted(values)
        n = len(values)
        q1 = values[n // 4]
        q3 = values[(n * 3) // 4]
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        return [v for v in values if v < lower or v > upper]

    def detect(self, values):
        outliers = self.detect_outliers_iqr(values)
        return {
            "success": True,
            "anomalies_detected": bool(outliers),
            "method": "STATISTICAL_IQR",
            "count": len(outliers),
            "outliers": outliers
        }
