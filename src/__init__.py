"""
BetFlow: SatoshiDice Blockchain Analytics Pipeline.

Core module for memory-optimized data ingestion, mapping, and preprocessing 
of Bitcoin transactions and SatoshiDice betting ledgers.
"""


from .config import (
    PROJECT_ROOT,
    DATA_DIR,
    RAW_DATA_DIR,
    PROCESSED_DATA_DIR,
    TRANSACTIONS_FILE,
    INPUTS_FILE,
    OUTPUTS_FILE,
    MAPPING_FILE,
    SATOSHI_DICE_FILE
)

from .data_loader import load_all_data