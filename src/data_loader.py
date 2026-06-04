import pandas as pd
import os
from .config import (
    TRANSACTIONS_FILE,
    INPUTS_FILE,
    OUTPUTS_FILE,
    MAPPING_FILE,
    SATOSHI_DICE_FILE
)

TRANSACTIONS_DTYPES = {
    'timestamp': 'uint32',
    'blockId': 'uint32',
    'txId': 'uint32',
    'isCoinbase': 'bool',     
    'fee': 'float64'
}

INPUTS_DTYPES = {
    'txId': 'uint32',
    'prevTxId': 'uint32',
    'prevTxpos': 'uint32'
}

OUTPUTS_DTYPES = {
    'txId': 'uint32',
    'position': 'uint32',
    'addressId': 'uint32',
    'amount': 'float64',
}

MAPPING_DTYPES = {
    'hash': 'string[pyarrow]',  # highly optimized for string storage
    'addressId': 'uint32',
}


def load_all_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load all datasets optimizing memory usage and parsing performance.
    """
    
    transactions = _load_data(
        TRANSACTIONS_FILE,
        TRANSACTIONS_DTYPES,
        names=list(TRANSACTIONS_DTYPES.keys()), 
        header=None,
    )  

    inputs = _load_data(
        INPUTS_FILE, 
        INPUTS_DTYPES,
        names=list(INPUTS_DTYPES.keys()),
        header=None,
    )

    outputs = _load_data(
        OUTPUTS_FILE,
        OUTPUTS_DTYPES,
        names=list(OUTPUTS_DTYPES.keys()),
        usecols=[0, 1, 2, 3],
        header=None,
    ) 

    mapping = _load_data(
        MAPPING_FILE,
        MAPPING_DTYPES,
        names=list(MAPPING_DTYPES.keys()),
        header=None,
    )

    satoshi_columns = [
        'Name', 'Address', 'WinOdds', 'PriceMultiplier', 
        'HousePercentage', 'ExpectReturn', 'MinimumBet', 'MaximumBet'
    ]

    satoshi_dice = pd.read_csv(
        SATOSHI_DICE_FILE,
        sep=r"\s{2,}",  # separators with 2 or more spaces
        skiprows=2,     # skip initial url
        names=satoshi_columns,
        engine='python'
    )  

    # Data cleaning and type conversion per Satoshi Dice
    for col in ['WinOdds', 'HousePercentage', 'ExpectReturn']:
        satoshi_dice[col] = satoshi_dice[col].str.rstrip('%').astype('float64')
    satoshi_dice['PriceMultiplier'] = satoshi_dice['PriceMultiplier'].str.rstrip('x').astype('float64')

    print(f"'satoshiDiceInfos.tsv' loaded successfully. Size: {satoshi_dice.memory_usage().sum() / 1024**2:.4f} MB")

    return transactions, inputs, outputs, mapping, satoshi_dice


def _load_data(file_path, dtypes, sep=",", usecols=None, names=None, header='infer') -> pd.DataFrame:
    """
    Helper function to load a CSV file with optimized settings.
    Parameters:
        file_path: path to the CSV file
        dtypes: dictionary of column data types for memory optimization
        sep: separator used in the CSV file (default is comma)
        usecols: list of columns to read (default is None, which reads all columns)
        names: list of column names to use (default is None, which infers from the file)
        header: row number to use as column names (default is 'infer', which infers from the file, set to None if names are provided)
    """

    df = pd.read_csv(file_path, dtype=dtypes, sep=sep, usecols=usecols, names=names, header=header, engine='pyarrow')

    memory_usage = df.memory_usage(deep=False).sum() / (1024 ** 2)
    print(f"'{os.path.basename(file_path)}' loaded successfully. Size: {memory_usage:.2f} MB")

    return df