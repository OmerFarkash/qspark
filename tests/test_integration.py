from sys import path as sys_path
from os import path as os_path
sys_path.append(os_path.abspath(os_path.join(os_path.dirname(__file__), '..', 'src')))

import pytest
from locates_task import csv_parser, distribute_locates

@pytest.fixture
def input_csv_path():
    # return os_path.join(os_path.dirname(__file__), 'test_data', 'other.csv')
    return os_path.join(os_path.dirname(__file__), 'test_data', 'complex.csv')

@pytest.fixture
def approved_locates():
    # return {
    #     'AAPL': 1570,  # ~87% of 1800 requested
    #     'GOOG': 800,   # 80% of 1000 requested
    #     'MSFT': 400    # 80% of 500 requested
    # }

    # agrigation for complex.csv
    return {
        'AAPL': 2550, # 75% of 3400 requested
        'MSFT': 1740, # 60% of 2900 requested
        'GOOGL': 2660, # 95% of 2800 requested
        'AMZN': 2190, # 73% of 3000 requested
        'TSLA': 864, # 27% of 3200 requested
    }


@pytest.fixture
def expected_distribution():
    return {
        # 'ClientA': {'AAPL': 900, 'GOOGL': 600},
        # 'ClientB': {'AAPL': 422, 'MSFT': 300},
        # 'ClientC': {'AAPL': 248, 'GOOG': 200},
        # 'ClientD': {'MSFT': 100}
        'Alice': {'AAPL': 400},
        'Bob': {'MSFT': 220},
        'Charlie': {'GOOGL': 200},
        'Dave': {'AMZN': 208},
        'Eve': {'AAPL': 438},
        'Frank': {'AAPL': 512},
        'Grace': {'MSFT': 500},
        'Heidi': {'AMZN': 647},
        'Ivan': {'GOOGL': 930},
        'Judy': {'TSLA': 300},
        'Karl': {'TSLA': 41},
        'Leo': {'GOOGL': 300},
        'Mallory': {'MSFT': 100},
        'Niaj': {'AAPL': 300},
        'Olivia': {'AMZN': 400},
        'Peggy': {'TSLA': 200},
        'Quentin': {'MSFT': 400},
        'Rupert': {'AAPL': 300},
        'Sybil': {'GOOGL': 300},
        'Trent': {'AMZN': 135},
        'Ursula': {'TSLA': 13},
        'Victor': {'AAPL': 600},
        'Wendy': {'MSFT': 520},
        'Xander': {'GOOGL': 930},
        'Yvonne': {'AMZN': 800},
        'Zack': {'TSLA': 310}
    }

def test_end_to_end_integration(input_csv_path, approved_locates, expected_distribution):
    # Get the parsed data from CSV
    clients_requests, _, req_by_symbol_clients_percentage = csv_parser(input_csv_path)
    # Distribute the locates using the predefined approved amounts
    distribution = distribute_locates(clients_requests, approved_locates, req_by_symbol_clients_percentage)
    
    # Verify the distribution matches expected results
    assert distribution == expected_distribution

