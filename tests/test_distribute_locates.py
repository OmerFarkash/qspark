from sys import path as sys_path
from os import path as os_path
sys_path.append(os_path.abspath(os_path.join(os_path.dirname(__file__), '..', 'src')))

import pytest
from locates_task import distribute_locates

@pytest.mark.parametrize(
    "clients_requests, approved_locates, req_by_symbol_clients_percentage, expected_distribution", [
         # Basic distribution case
        (
            {
                'Client1': {'ABC': 300},
                'Client2': {'QQQ': 100, 'ABC': 200},
                'Client3': {'TTT': 100}
            },
            {
                'ABC': 400,  # 80% of 500 requested
                'QQQ': 80,   # 80% of 100 requested
                'TTT': 80    # 80% of 100 requested
            },
            {
                'ABC': {'Client1': 0.6, 'Client2': 0.4},
                'QQQ': {'Client2': 1.0},
                'TTT': {'Client3': 1.0}
            },
            {
                'Client1': {'ABC': 200},
                'Client2': {'ABC': 200, 'QQQ': 80},
                'Client3': {'TTT': 80}
            }
        ),
        # Distribution with only some symbols approved
        ( 
            {
                'Client1': {'ABC': 300},
                'Client2': {'QQQ': 100, 'ABC': 200},
                'Client3': {'TTT': 100}
            },
            {
                'ABC': 450,
                'QQQ': 90
            },
            {
                'ABC': {'Client1': 0.6, 'Client2': 0.4},
                'QQQ': {'Client2': 1.0},
                'TTT': {'Client3': 1.0}
            },
            {
                'Client1': {'ABC': 250},
                'Client2': {'ABC': 200, 'QQQ': 90},
                'Client3': {}
            }
        ), 
        # more complex distribution case
        (
            {
                'ClientA' : {'AAPL':1000, 'GOOG':800},
                'ClientB' : {'AAPL':500, 'MSFT':400},
                'ClientC' : {'AAPL':300, 'GOOG':200},
                'ClientD' : {'MSFT':100}
            },
            {
                'AAPL': 1570,  # some of 1800 requested
                'GOOG': 800,   # 80% of 1000 requested
                'MSFT': 400    # 80% of 500 requested
            },
            {
                'AAPL' : {'ClientA': 0.5556, 'ClientB': 0.2778, 'ClientC': 0.1667},
                'GOOG' : {'ClientA': 0.8, 'ClientC': 0.2},
                'MSFT' : {'ClientB': 0.8, 'ClientD': 0.2}
            },
            {
                'ClientA' : {'AAPL':900, 'GOOG':600},
                'ClientB' : {'AAPL':422, 'MSFT':300},
                'ClientC' : {'AAPL':248, 'GOOG':200},
                'ClientD' : {'MSFT':100}
            }
        )
    ] 
)
def test_distribute_locates(clients_requests, approved_locates, req_by_symbol_clients_percentage, expected_distribution):
    distribution = distribute_locates(clients_requests, approved_locates, req_by_symbol_clients_percentage)
    assert distribution == expected_distribution