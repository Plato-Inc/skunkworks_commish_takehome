from io import StringIO

import pandas as pd
from fastapi import UploadFile


def _is_valid_csv_file(file: UploadFile) -> bool:
    """Check if a single file is a valid CSV file."""
    return (
        file.filename is not None
        and file.filename.strip() != ""
        and file.filename.lower().endswith('.csv')
    )

def _validate_csv_files(*files: UploadFile) -> bool:
    """Validate that all uploaded files are CSV files."""
    if not files:
        return False
    for file in files:
        if not _is_valid_csv_file(file):
            return False
    return True

def _read_file_content(file: UploadFile) -> str:
    """Read file content and reset file pointer."""
    content = file.file.read()
    file.file.seek(0)
    return content.decode('utf-8')

def _parse_csv_content(content: str, file_name: str) -> pd.DataFrame:
    """Parse CSV content into a DataFrame."""
    if not content.strip():
        raise ValueError(f"{file_name} is empty")
    try:
        return pd.read_csv(StringIO(content))
    except pd.errors.EmptyDataError:
        raise ValueError(f"{file_name} contains no data")
    except pd.errors.ParserError as e:
        raise ValueError(f"{file_name} has invalid CSV format: {str(e)}")

def _read_csv_file(file: UploadFile, file_name: str) -> pd.DataFrame:
    """Read and validate CSV file content."""
    try:
        content = _read_file_content(file)
        return _parse_csv_content(content, file_name)
    except UnicodeDecodeError:
        raise ValueError(f"{file_name} contains invalid UTF-8 encoding")
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        raise ValueError(f"Failed to process {file_name}: {str(e)}") 