from pathlib import Path

# Radice dinamica del progetto
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Cartelle principali
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Percorsi completi per i singoli dataset grezzi (raw)
TRANSACTIONS_FILE = RAW_DATA_DIR / "transactions.csv"
INPUTS_FILE = RAW_DATA_DIR / "inputs.csv"
OUTPUTS_FILE = RAW_DATA_DIR / "outputs.csv"
MAPPING_FILE = RAW_DATA_DIR / "mapAddr2Ids8708820.csv"
SATOSHI_DICE_FILE = RAW_DATA_DIR / "satoshiDiceInfos.tsv"
