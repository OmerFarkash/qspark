import csv, os

def valid_req(row: dict[str, str]) -> None | tuple[str,str,int]:
    """Basic validation for a single row. 
    return None on bad input.
    Returns all the valid fields on success.
    """
    # read fields by header names
    try:
        client = row.get('client_name')
        symbol = row.get('symbol')
        num_of_locates_req = row.get('number_of_locates_requested')

        # missing header fields - there might be a fix but I rather to fix the csv file
        if client is None or symbol is None or num_of_locates_req is None:
            return None
        # empty strings
        if str(client).strip() == "" or str(symbol).strip() == "":
            return None
        
        num_of_locates_req = int(num_of_locates_req)
        # invalid number of locates
        if num_of_locates_req % 100 != 0 or num_of_locates_req <= 0:
            return None
        
        return client, symbol, num_of_locates_req
    except Exception as e:
        return None


def csv_parser(file_path: str) -> tuple[dict[str, dict[str, int]], dict[str, int], dict[str, dict[str, float]]]:
    """Parses the CSV file and returns:
    - a dictionary of clients requests: {client_name: {symbol: num_of_locates_requested}}
    - a dictionary of aggregate symbols requests: {symbol: total_num_of_locates_requested}
    - a dictionary of requested locates percentages by symbol: {symbol: {client_name: percentage_of_requests}}
    """
    clients_requests: dict[str, dict[str, int]] = {}
    aggregate_symbols: dict[str, int] = {}
    req_by_symbol_clients_percentage: dict[str, dict[str, float]] = {}
    try:
        _, extension = os.path.splitext(file_path)

        # Check if the extension is '.csv'
        if extension.lower() != '.csv':
            raise ValueError(f"the file is not a .csv file: {file_path}")
        # skipinitialspace=True trims whitespace following the delimiter
        with open(file_path, 'r', newline='') as csv_file:
            reader = csv.DictReader(csv_file, skipinitialspace=True)

            if reader.fieldnames is None or len(reader.fieldnames) != 3:
                raise Exception("the csv file is in the wrong format")

            for row in reader:
                # validate and convert
                result = valid_req(row)
                if result is None:
                    # invalid row - skip
                    continue
                client, symbol, num_of_locates_req = result

                # each-client requests
                client_reqs = clients_requests.setdefault(client, {})
                # each client, symbol appears once
                client_reqs[symbol] = num_of_locates_req

                # overall symbol aggregation
                aggregate_symbols[symbol] = aggregate_symbols.get(symbol, 0) + num_of_locates_req

                # track requested locates by symbol (convert to percentages after file read)
                symbol_clients = req_by_symbol_clients_percentage.setdefault(symbol, {})
                symbol_clients[client] = num_of_locates_req

            # convert per-symbol client requests to percentages (do not mutate while iterating)
            for symbol, client_requests in req_by_symbol_clients_percentage.items():
                total_requested = aggregate_symbols[symbol]
                # build a new dict of percentages
                req_by_symbol_clients_percentage[symbol] = {
                    client: req / total_requested for client, req in client_requests.items()
                }

    # common exceptions
    except Exception as e:
        if isinstance(e, FileNotFoundError):
            raise FileExistsError("invalid file path - the file not found")
        elif isinstance(e, TypeError):
            raise TypeError("the file path is not a valid string")
        elif isinstance(e, ValueError):
            raise Exception("Failed to parse CSV") from e
        else:
            raise Exception(f"Error: {e}")

    return clients_requests, aggregate_symbols, req_by_symbol_clients_percentage

def distribute_locates(clients_requests: dict[str, dict[str, int]], approved_locates: dict[str, int],
                       req_by_symbol_clients_percentage: dict[str, dict[str, float]]) -> dict[str, dict[str, int]]:
    """Distributes the approved locates among clients requests proportionally.
    returns a dictionary of distributed locates: {client_name: {symbol: num_of_locates_distributed}}"""
    # client -> {symbol -> num}
    distributed_locates: dict[str, dict[str, int]] = {client: {} for client in clients_requests.keys()}

    def rounding_100(curr, symbol) -> None | list[str, int]:  
        # order by the min change in oreder to get to a multiple of 100
        filtered_items = [list(item) for item in curr.items() if item[1] % 100 != 0]
        sorted_and_filtered = sorted(filtered_items, key=lambda item: item[1] % 100, reverse=True)
        total_to_distribute = 0

        # collecting all reminders to distribute
        for i, (_, val) in enumerate(sorted_and_filtered):
            reminder = val % 100
            total_to_distribute += reminder
            # sorted_and_filtered[i][1] = val - reminder
        times = int(total_to_distribute / 100)
        # if sum of reminders is less than 100 no need to distribute
        if not times:
            return None
        
        # figure how much we need of rounding the cloesest to it.
        grab_for_distribution = 0
        for i in range(times):
            grab_for_distribution += 100 - (sorted_and_filtered[i][1] % 100)
            # act like we rounded them already
            sorted_and_filtered[i][1] += 100 - (sorted_and_filtered[i][1] % 100)

        emptied_clients = 0
        # grab from the lowest ones to distribute to the top ones
        while grab_for_distribution > 0:
            size_of_relevants = len(sorted_and_filtered) - (emptied_clients + times) # of clients that can give locates
            to_take = int(grab_for_distribution / size_of_relevants) # how much to take from each client

            if not to_take:
                for i in range(grab_for_distribution):
                    index = size_of_relevants + times - 1 - (i % size_of_relevants)
                    sorted_and_filtered[index][1] -= 1
                grab_for_distribution = 0
                break

            for i in range (size_of_relevants + times - 1, times - 1, -1): # from the lowest to the highest that gave locates
                # if we can take the full amount
                if (sorted_and_filtered[i][1] % 100) - to_take >= 0:
                    sorted_and_filtered[i][1] -= to_take
                    grab_for_distribution -= to_take
                    # if we emptied this client
                    if sorted_and_filtered[i][1] % 100 == 0:
                        emptied_clients += 1
                # else if we can't take the full amount
                else: 
                    to_take = sorted_and_filtered[i][1] % 100
                    sorted_and_filtered[i][1] -= to_take
                    emptied_clients += 1
                    grab_for_distribution -= to_take
                    break
        return sorted_and_filtered


    def distribute_by_symbol() -> None:
        """Distributes approved locates by symbol among clients.
        returns a dictionary of distributed locates by symbol."""
        # go over relevent symbols only
        for symbol, total in approved_locates.items():
            curr = {}
            rounding = False
            for client, proportion in req_by_symbol_clients_percentage[symbol].items():
                # find portion by number
                amount = proportion * total

                # make sure to distribute the whole approved number
                converted = int(amount)
                if amount - converted > 0.5:
                    amount = converted + 1
                else: 
                    amount = converted
                
                curr[client] = amount

                # client can't get more then requested
                max_allocate = min(amount, clients_requests[client][symbol])
                distributed_locates[client][symbol] = max_allocate

                # got by proportion 
                if max_allocate != clients_requests[client][symbol]:
                    rounding = True
            # got by proportion - try to redistribute
            if rounding: 
                distribute_list = rounding_100(curr, symbol)
                if distribute_list:
                    for client, value in distribute_list:
                        distributed_locates[client][symbol] = value
            
        return
    
    distribute_by_symbol()
    return distributed_locates
    


def request_locates(requested_locates: dict[str, int]) -> dict[str, int]:
    """A black box function that approves locates
    according to some internal logic.
    This is just a way for me to simulate locate approvals instead of the API call.
    """
    from random import random, uniform
    approved_locates = {}
    for symbol, requested in requested_locates.items():
        # Simulate partial approval: randomly skip some symbols
        if random() < 0.7:  # 70% chance to approve this symbol
            # Simulate partial approval: approve a random portion up to min(requested, 1000)
            max_approve = min(requested, 1000)
            # Approve between 50% and 100% of max_approve
            approved = int(max_approve * uniform(0.5, 1.0))
            approved_locates[symbol] = approved
        # else: skip this symbol (not approved)
    return approved_locates

if __name__ == '__main__':
    # csv_path = r'.\csvs\basic_example.csv'
    csv_path = r'.\tests\test_data\complex.csv'
    clients_requests, aggregate_symbols, req_by_symbol_clients_percentage = csv_parser(csv_path)
    # simulate API call
    # approved = request_locates(aggregate_symbols)
    approved ={
        'AAPL': 2550, # 75% of 3400 requested
        'MSFT': 1740, # 60% of 2900 requested
        'GOOGL': 2660, # 95% of 2800 requested
        'AMZN': 2190, # 73% of 3000 requested
        'TSLA': 864, # 27% of 3200 requested
    }
    # compute distribution
    distributed = distribute_locates(clients_requests, approved, req_by_symbol_clients_percentage)
    print("Final distribution:")
    print(distributed)
