"""
Data cleaning and processing pipeline for hospital complexity data.

This module contains functions to process raw Excel files and prepare
data for machine learning predictions.
"""

from .data_cleaner import procesar_excel_completo

__all__ = [
    'procesar_excel_completo',
]

