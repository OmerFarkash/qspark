import csv, os

# Constants
VALUE_OF_ITEM = 1

def valid_req(row: dict[str, str]) -> None | tuple[str,str,int,int]:
    """Basic validation for a single row.
    input: dictionary representing a CSV row - {client_name, symbol, number_of_locates_requested, round_lot_size}.
    returns: None on bad input.
             all the valid fields on success - (client_name, symbol, number_of_locates_requested, round_lot_size).
    """
    # read fields by header names
    try:
        client = row.get('client_name')
        symbol = row.get('symbol')
        num_of_locates_req = row.get('number_of_locates_requested')
        round_size = row.get("round_lot_size")
        # missing header fields - there might be a fix but I rather to fix the csv file
        if client is None or symbol is None or num_of_locates_req is None or round_size is None:
            return None
        # empty strings
        if str(client).strip() == "" or str(symbol).strip() == "":
            return None
        
        # invalid number of rounding
        round_size = int(round_size)
        if round_size <= 0:
            return None

        num_of_locates_req = int(num_of_locates_req)
        # invalid number of locates
        if num_of_locates_req % round_size != 0 or num_of_locates_req <= 0:
            return None
        
        return client, symbol, num_of_locates_req, round_size
    except Exception as e:
        return None


def csv_parser(file_path: str) -> tuple[dict[str, dict[str, int]], dict[str, int], dict[str, dict[str, float]]]:
    """Parses the CSV file into data structures.
    input: path to the CSV file.
    returns: a tuple of three dictionaries:
    - a dictionary of clients requests: {client_name: {symbol: num_of_locates_requested}}
    - a dictionary of aggregate symbols requests: {symbol: total_num_of_locates_requested}
    - a dictionary of requested locates percentages by symbol: {symbol: {client_name: percentage_of_requests}}
    - a dictionary of chunk sizes by symbol: {symbol: round_size}
    """
    clients_requests: dict[str, dict[str, int]] = {}
    aggregate_symbols: dict[str, int] = {}
    req_by_symbol_clients_percentage: dict[str, dict[str, float]] = {}
    chunk_pr_symbol: dict[str, int] = {}
    try:
        _, extension = os.path.splitext(file_path)

        # Check if the extension is '.csv'
        if extension.lower() != '.csv':
            raise ValueError(f"the file is not a .csv file: {file_path}")
        # skipinitialspace=True trims whitespace following the delimiter
        with open(file_path, 'r', newline='') as csv_file:
            reader = csv.DictReader(csv_file, skipinitialspace=True)

            # validate headers length
            if reader.fieldnames is None or len(reader.fieldnames) != 4:
                raise Exception("the csv file is in the wrong format")

            for row in reader:
                result = valid_req(row)
                if result is None:
                    # invalid row - skip
                    continue
                client, symbol, num_of_locates_req, round_size = result

                # track chunk sizes - only the first one matters
                existing_round_size = chunk_pr_symbol.get(symbol)
                if existing_round_size is None:
                    chunk_pr_symbol[symbol] = round_size

                # each-client requests
                client_reqs = clients_requests.setdefault(client, {})
                # each client, symbol appears once so no need to check for existing symbol
                client_reqs[symbol] = num_of_locates_req

                # overall symbol aggregation
                aggregate_symbols[symbol] = aggregate_symbols.get(symbol, 0) + num_of_locates_req

                # track requested locates by symbol (convert to percentages after file read)
                symbol_clients = req_by_symbol_clients_percentage.setdefault(symbol, {})
                symbol_clients[client] = num_of_locates_req

            # convert per-symbol client requests to percentages
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

    return clients_requests, aggregate_symbols, req_by_symbol_clients_percentage, chunk_pr_symbol


def distribute_locates(clients_requests: dict[str, dict[str, int]], approved_locates: dict[str, int],
                       req_by_symbol_clients_percentage: dict[str, dict[str, float]], chunk_pr_symbol: dict[str, int]) -> dict[str, dict[str, int]]:
    """Distributes the approved locates among clients requests proportionally.
    input:
    - clients_requests: {client_name: {symbol: num_of_locates_requested}}
    - approved_locates: {symbol: num_of_locates_approved}
    - req_by_symbol_clients_percentage: {symbol: {client_name: percentage_of_requests}}
    - chunk_pr_symbol: {symbol: round_lot_size}
    returns a dictionary of distributed locates: {client_name: {symbol: num_of_locates_distributed}}
    """
    # client : {symbol : num}
    distributed_locates: dict[str, dict[str, int]] = {client: {} for client in clients_requests.keys()}

    def rounding_chunks(distribute_by_proportion: dict[str, int], round_lot_size: int) -> None | list[str, int]:
        """Rounds the distributed locates to the nearest chunk size (round_lot_size).
        input: distribute_by_proportion - {client_name: num_of_locates_distributed}
        returns a list of tuples (client_name, rounded_num_of_locates_distributed) or None if no rounding needed.
        """
        # order by the min change in oreder to get to a multiple of round_lot_size
        filtered_items = [list(item) for item in distribute_by_proportion.items() if item[VALUE_OF_ITEM] % round_lot_size != 0]
        sorted_and_filtered = sorted(filtered_items, key=lambda item: item[VALUE_OF_ITEM] % round_lot_size, reverse=True)

        # collecting all reminders to distribute
        total_to_distribute = 0
        for i, (_, val) in enumerate(sorted_and_filtered):
            reminder = val % round_lot_size
            total_to_distribute += reminder
        times = int(total_to_distribute / round_lot_size)
        # if sum of reminders is less than round_lot_size no need to distribute
        if not times:
            return None
        
        # figure how much we need of rounding the cloesest to it.
        grab_for_distribution = 0
        for i in range(times):
            grab_for_distribution += round_lot_size - (sorted_and_filtered[i][VALUE_OF_ITEM] % round_lot_size)
            # act like we rounded them already
            sorted_and_filtered[i][VALUE_OF_ITEM] += round_lot_size - (sorted_and_filtered[i][VALUE_OF_ITEM] % round_lot_size)

        emptied_clients = 0
        # grab from the lowest ones to distribute to the top ones
        while grab_for_distribution > 0:
            size_of_relevants = len(sorted_and_filtered) - (emptied_clients + times) # of clients that can give locates
            chunk_to_redistribute = int(grab_for_distribution / size_of_relevants) # how much to take from each client

            # if we can't take a full chunk from each client - take 1 from the lowest ones
            if not chunk_to_redistribute:
                for i in range(grab_for_distribution):
                    index = size_of_relevants + times - 1 - (i % size_of_relevants)
                    sorted_and_filtered[index][VALUE_OF_ITEM] -= 1
                grab_for_distribution = 0
                break
            
            # from the lowest to the highest that gave locates
            for i in range (size_of_relevants + times - 1, times - 1, -1): 
                # if we can take the full amount
                if (sorted_and_filtered[i][VALUE_OF_ITEM] % round_lot_size) - chunk_to_redistribute >= 0:
                    sorted_and_filtered[i][VALUE_OF_ITEM] -= chunk_to_redistribute
                    grab_for_distribution -= chunk_to_redistribute
                    # if we emptied this client
                    if sorted_and_filtered[i][VALUE_OF_ITEM] % round_lot_size == 0:
                        emptied_clients += 1
                # else if we can't take the full amount
                else: 
                    chunk_to_redistribute = sorted_and_filtered[i][VALUE_OF_ITEM] % round_lot_size
                    sorted_and_filtered[i][VALUE_OF_ITEM] -= chunk_to_redistribute
                    emptied_clients += 1
                    grab_for_distribution -= chunk_to_redistribute
                    break
        return sorted_and_filtered


    def distribute_by_symbol() -> None:
        """Distributes approved locates by symbol among clients.
        changes the distributed_locates dictionary in place."""
        # go over relevent symbols only
        for symbol, total in approved_locates.items():
            distribute_by_proportion = {}
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
                distribute_by_proportion[client] = amount

                # client can't get more then requested
                max_allocate = min(amount, clients_requests[client][symbol])
                distributed_locates[client][symbol] = max_allocate

                # client got by proportion - check if rounding is needed
                if max_allocate != clients_requests[client][symbol]:
                    rounding = True
            # try to redistribute leftovers
            if rounding: 
                distribute_list = rounding_chunks(distribute_by_proportion, chunk_pr_symbol[symbol])
                if distribute_list:
                    for client, value in distribute_list:
                        distributed_locates[client][symbol] = value
            
        return
    
    distribute_by_symbol()
    return distributed_locates
    
def create_results_csv(distributed_locates: dict[str, dict[str, int]], output_path: str) -> None:
    """Creates a CSV file with the distributed locates results.
    input:
    - distributed_locates: {client_name: {symbol: num_of_locates_distributed}}
    - output_path: path to the output CSV file.
    returns: None on success, raises Exception on failure.
    """
    try:
        with open(output_path, 'w', newline='') as csv_file:
            fieldnames = ['client_name', 'symbol', 'number_of_locates_allocated']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            # write each client's distributed locates
            for client, symbols_granted in distributed_locates.items():
                for symbol, num_of_locates in symbols_granted.items():
                    writer.writerow({
                        'client_name': client,
                        'symbol': f" {symbol}",
                        'number_of_locates_allocated': f" {num_of_locates}"
                    })
    except Exception as e:
        raise Exception(f"Failed to write results CSV: {e}")


def request_locates(requested_locates: dict[str, int]) -> dict[str, int]:
    """A black box function that approves locates
    according to some internal logic.
    This is just a way for me to simulate locate approvals instead of the API call.
    input: requested_locates - {symbol: num_of_locates_requested}
    returns: approved_locates - {symbol: num_of_locates_approved}
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
    csv_path = r'.\tests\test_data\complex.csv'
    clients_requests, aggregate_symbols, req_by_symbol_clients_percentage, chunk_pr_symbol = csv_parser(csv_path)
    # simulate API call
    approved = request_locates(aggregate_symbols)

    # approved ={
    #     'AAPL': 2550, # 75% of 3400 requested
    #     'MSFT': 1740, # 60% of 2900 requested
    #     'GOOGL': 2660, # 95% of 2800 requested
    #     'AMZN': 2190, # 73% of 3000 requested
    #     'TSLA': 864, # 27% of 3200 requested
    # }

    # compute distribution
    distributed = distribute_locates(clients_requests, approved, req_by_symbol_clients_percentage, chunk_pr_symbol)
    
    # write results to CSV
    output_csv_path = r'.\results.csv'
    create_results_csv(distributed, output_csv_path)
