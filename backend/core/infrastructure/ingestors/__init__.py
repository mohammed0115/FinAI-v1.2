"""
Ingestion Infrastructure — structured file parsers (CSV, JSON).

Each class implements the IIngestionProvider protocol from domain/interfaces.py.
"""
from .csv_ingestor import CsvIngestor
from .json_ingestor import JsonIngestor

__all__ = ["CsvIngestor", "JsonIngestor"]
