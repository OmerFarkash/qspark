from sys import path as sys_path
from os import path as os_path
sys_path.append(os_path.abspath(os_path.join(os_path.dirname(__file__), '..', 'src')))

from locates_task import csv_parser
import pytest
import pathlib

# Test for valid CSV parsing
@pytest.mark.parametrize(
    "csv_relpath,expected_clients_requests,expected_aggregate_symbols,expected_req_by_symbol_clients_percentage",
    [
        (
            "test_data/basic_example.csv",
            {
                'Client1': {'ABC': 300},
                'Client2': {'QQQ': 100, 'ABC': 200},
                'Client3': {'TTT': 100}
            },
            {
                'ABC': 500,
                'QQQ': 100,
                'TTT': 100
            },
            {
                'ABC': {'Client1': 0.6, 'Client2': 0.4},
                'QQQ': {'Client2': 1.0},
                'TTT': {'Client3': 1.0}
            }
        )
    ]
)
def test_csv_parser_valid_file(csv_relpath, expected_clients_requests, expected_aggregate_symbols,
                               expected_req_by_symbol_clients_percentage):
    test_file = pathlib.Path(__file__).parent / csv_relpath
    clients_requests, aggregate_symbols, req_by_symbol_clients_percentage = csv_parser(str(test_file))

    assert clients_requests == expected_clients_requests
    assert aggregate_symbols == expected_aggregate_symbols
    assert req_by_symbol_clients_percentage == expected_req_by_symbol_clients_percentage

# Test for the "TypeError" branch
@pytest.mark.parametrize("invalid_input", [
    123,          # Pass an integer
    None,         # Pass None
    ["path.csv"]  # Pass a list
])
def test_parser_type_error(invalid_input):
    """
    Tests the 'isinstance(e, TypeError)' branch.
    This is triggered when a non-string/path is passed to open().
    """
    with pytest.raises(TypeError, match="the file path is not a valid string"):
        csv_parser(invalid_input)


# Test for the "FileNotFoundError" branch
def test_parser_file_not_found():
    """
    Tests the 'isinstance(e, FileNotFoundError)' branch.
    This is triggered by passing a path that does not exist.
    """
    # NOTE: Your code raises FileExistsError, so we check for that
    with pytest.raises(FileExistsError, match="invalid file path - the file not found"):
        csv_parser("path/that/does/not/exist.csv")


# Test for the "ValueError" branch (malformed CSV)
def test_parser_value_error_not_a_csv(tmp_path):
    """
    Tests the 'isinstance(e, ValueError)' branch.
    This is triggered by a file that isn't CSV-formatted,
    which causes csv.DictReader to raise an error (like csv.Error, 
    which your code might be catching as ValueError or just Exception).
    """
    # Create a dummy file in the temp directory
    p = tmp_path / "invalid.txt"
    p.write_text("This is just plain text, not a CSV file.")
    
    with pytest.raises(Exception, match="Failed to parse CSV"):
        csv_parser(str(p))


# Test for the "wrong format" (column count)
@pytest.mark.parametrize("bad_csv_content", [
    "col1,col2\nval1,val2",                 # Only 2 columns
    "col1,col2,col3,col4\nval1,val2,val3,val4" # 4 columns
])
def test_parser_wrong_column_count(tmp_path, bad_csv_content):
    """
    Tests the 'len(reader.fieldnames) != 3' check.
    This is triggered by a CSV that has 2 or 4 columns.
    """
    p = tmp_path / "wrong_columns.csv"
    p.write_text(bad_csv_content)
    
    with pytest.raises(Exception, match="the csv file is in the wrong format"):
        csv_parser(str(p))