from sys import path as sys_path
from os import path as os_path
sys_path.append(os_path.abspath(os_path.join(os_path.dirname(__file__), '..', 'src')))

from locates_task import valid_req
import pytest

# Tests for valid_req function
@pytest.mark.parametrize("row, expected", [
    ({'client_name': 'ClientA', 'symbol': 'AAPL', 'number_of_locates_requested': '200'},
     ('ClientA', 'AAPL', 200)), # Valid normal case
    ({'client_name': ' ClientB ', 'symbol': ' MSFT ', 'number_of_locates_requested': ' 300 '},
     (' ClientB ', ' MSFT ', 300)),  # Valid case with leading/trailing spaces
])

def test_valid_cases(row, expected):
    assert valid_req(row) == expected

# Tests for invalid cases
@pytest.mark.parametrize("row", [
    {'client_name': None, 'symbol': 'GOOGL', 'number_of_locates_requested': '400'}, # Missing client_name
    {'client_name': ' ClientD ', 'symbol': None, 'number_of_locates_requested': ' 500 '}, # Missing symbol
    {'client_name': 'ClientE', 'symbol': 'AMZN', 'number_of_locates_requested': None}, # Missing number_of_locates_requested
    {'client_name': '   ', 'symbol': 'TSLA', 'number_of_locates_requested': '600'}, # Empty client_name
    {'client_name': 'ClientF', 'symbol': '   ', 'number_of_locates_requested': '700'}, # Empty symbol
    {'client_name': 'ClientG', 'symbol': 'NFLX', 'number_of_locates_requested': '-100'}, # Negative number_of_locates_requested
    {'client_name': 'ClientH', 'symbol': 'FB', 'number_of_locates_requested': '250'}, # Non-multiple of 100
    {'client_name': 'ClientI', 'symbol': 'TWTR', 'number_of_locates_requested': 'abc'}, # Non-integer number_of_locates_requested
    {'client_name': 'ClientC', 'symbol': 'GOOGL', 'number_of_locates_requested': '0'} # invalid case with zero requested
])
def test_invalid_cases(row):
    assert valid_req(row) is None

# Tests for exception handling

# Case helper that raises from .get()
class BadRow:
    def get(self, key):
        raise RuntimeError("boom")

@pytest.mark.parametrize("row", [
    BadRow(),  # object whose .get() raises
    123        # completely wrong type (no .get)
])
def test_exception_handling(row):
    assert valid_req(row) is None

# Additional edge cases
def test_empty_dict():
    assert valid_req({}) is None

def test_wrong_header_names():
    row = {'client1': 'ClientJ', 'AAPL': 'IBM', '200': '100'}
    assert valid_req(row) is None