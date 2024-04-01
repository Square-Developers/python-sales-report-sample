#!/opt/homebrew/bin/python3

# Copyright 2024 Square Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys, os, argparse, datetime

from square.client import Client
from square.http.auth.o_auth_2 import BearerAuthCredentials
from dotenv import load_dotenv
from prettytable import PrettyTable
from collections import defaultdict
import csv

SEED_DATA_REFERENCE_ID = "SEED_DATA"

# Process all the orders between start_date and end_date
def get_orders():
    limit = 25  # max number of orders per page

    print("start date: " + start_date + ", end date: " + end_date)

    print("Retrieving orders from ", start_date, " to ", end_date, "...")

    # Get the first page of orders
    result = client.orders.search_orders(
        body={
            "location_ids": [location_id],
            "limit": limit,
            "query": {
                "filter": {
                    "source_filter": {"source_names": [SEED_DATA_REFERENCE_ID]},
                    "state_filter": {"states": ["COMPLETED"]},
                    "date_time_filter": {
                        "closed_at": {"start_at": start_date, "end_at": end_date}
                    },
                },
                "sort": {"sort_field": "CLOSED_AT"},
            },
        }
    )

    if result.is_success():
        while (result.body != {}) and ("orders" in result.body.keys()):
            # Walk through each order on the current page
            for order in result.body["orders"]:               

                # Get basic for this order's items, and save it to the item_tally
                if "line_items" in order:
                    for line_item in order["line_items"]:
                        # Get basic info about a particular item, and save it to the item_tally
                        if "catalog_object_id" in line_item:
                            item_id = line_item["catalog_object_id"]
                            item_ids.append(item_id)
                            # Check if this itemId is already in the item_tally, if not, add it
                            if not item_id in item_tally:
                                item_tally.update(
                                    {
                                        item_id: {
                                            "qtySold": int(line_item["quantity"]),
                                             "total_sales": int(line_item["base_price_money"]["amount"]) * int(line_item["quantity"])
                                            }
                                        }
                                )
                            else:
                                # update the existing item_id
                                item_tally.update(
                                    {
                                        item_id: {
                                            # Add the quantity sold to the existing quantity
                                            "qtySold": int(
                                                item_tally[item_id].get("qtySold")
                                            )
                                            + int(line_item["quantity"]),
                                            # Add the total sales to the existing total sales 
                                            "total_sales": int(
                                                item_tally[item_id].get("total_sales")) 
                                                + int(line_item["base_price_money"]["amount"]) * int(line_item["quantity"])

                                        }
                                    }
                                )
                            # set the name, and variation_name for this item_id
                            item_tally[item_id]["name"] = line_item["name"]
                            item_tally[item_id]["variation_name"] = line_item[
                                "variation_name"
                            ]

                        else:
                            # No catalog info available (an ad hoc item, perhaps?)
                            print("This line item doesn't have a catalog_object_id")

                # No items here.  Next...
                else:
                    print("This order doesn't have any line items")

            # If the previous call returned a cursor, then get the next page of orders
            if result.cursor:
                result = client.orders.search_orders(
                    body={
                        "location_ids": [location_id],
                        "limit": limit,
                        "query": {
                            "filter": {
                                "source_filter": {"source_names": [SEED_DATA_REFERENCE_ID]},
                                "state_filter": {"states": ["COMPLETED"]},
                                "date_time_filter": {
                                    "closed_at": {
                                        "start_at": start_date,
                                        "end_at": end_date,
                                    }
                                },
                            },
                            "sort": {"sort_field": "CLOSED_AT"},
                        },
                        "cursor": result.cursor,
                    }
                )

            # If there isn't a cursor, then we're done getting orders
            else:
                break
        if item_ids:
            get_catalog_info_bulk(item_ids)
            get_inventory_counts_bulk(item_ids)

    # In case of errors with SearchOrders...
    elif result.is_error():
        handle_error(result.errors)


# Define a function to get catalog item details in bulk
def get_catalog_info_bulk(item_ids):
    try:
        result = client.catalog.batch_retrieve_catalog_objects(body={"object_ids": item_ids})
        if result.is_success():
            if result.body:
                for catalog_object in result.body["objects"]:
                    item_id = catalog_object["id"]
                    item_variation_data = catalog_object.get("item_variation_data", {})
                    sku = item_variation_data.get("sku", "N/A")
                    priceEach = item_variation_data.get("price_money")

                    item_tally[item_id]["sku"] = sku
                    item_tally[item_id]["priceEach"] = priceEach

    except Exception as e:
        handle_error([{"code": "API_ERROR", "detail": str(e)}])

# Retrieve quantity info for an item, and save it in the item_tally.
# (Note that Square only keeps track of quantities if track_inventory
# (in the CatalogItemVariation object) is set to true.
def get_inventory_counts_bulk(item_ids):
    try:
        result = client.inventory.batch_retrieve_inventory_counts(
            body={"catalog_object_ids": item_ids}
        )

        if result.is_success():
            if result.body:
                for inventory_count in result.body["counts"]:
                    item_id = inventory_count["catalog_object_id"]
                    quantity = inventory_count["quantity"]
                    item_tally[item_id]["qtyRemaining"] = quantity

    except Exception as e:
        handle_error([{"code": "API_ERROR", "detail": str(e)}])


# Generate the sales report
def print_sales_report():
    table = PrettyTable()

    # Define table columns
    table.field_names = ["ID", "Qty Sold", "Total Sales", "Currency", "Name", "Variation Name", "SKU", "Qty Remaining"]
    total_sales_sum = 0
    # Add data rows
    for key, value in item_tally.items():
        table.add_row([
            key,
            value["qtySold"],
            "${:,.2f}".format(value["total_sales"] / 100),
            value["priceEach"]["currency"] if "priceEach" in value else 'N/A',
            value["name"],
            value["variation_name"],
            value["sku"] if "sku" in value else 'N/A',
            value["qtyRemaining"] if "qtyRemaining" in value else "N/A"

        ])
        total_sales_sum += value["total_sales"]

    # Print the table
    print(table)
    print(f"Total Sales: ${total_sales_sum / 100}")

def write_sales_to_csv():
    # CSV file path
    csv_file = 'sales_report.csv'

    # Write data to CSV file
    with open(csv_file, 'w', newline='') as file:
        writer = csv.writer(file)

        # Write header row
        writer.writerow(["ID", "Qty Sold", "Total Sales", "Currency", "Name", "Variation Name", "SKU", "Qty Remaining"])

        # Write data rows
        for key, value in item_tally.items():
            writer.writerow([
                key,
                value["qtySold"],
                value["total_sales"],
                value["priceEach"]["currency"] if "priceEach" in value else 'N/A',
                value["name"],
                value["variation_name"],
                value["sku"] if "sku" in value else 'N/A',
                value["qtyRemaining"] if "qtyRemaining" in value else "N/A"
            ])
    print(f'Sales Report has been written to {csv_file}')   

# Ensure dates adhere to RFC 3339 format
def check_date_format(dt):
    try:
        dt = datetime.datetime.fromisoformat(dt)
    except ValueError:
        print(dt, ": Invalid date or date format - use RFC 3339 format")
        exit(1)
    print("Date: ", dt.isoformat())
    return dt.isoformat()


# Error handler
def handle_error(errors):
    print("Exception:")
    for err in errors:
        print(f"\tcategory: {err['category']}")
        print(f"\tcode: {err['code']}")
        print(f"\tdetail: {err['detail']}")
    sys.exit(1)


if __name__ == "__main__":
    # We don't recommend running this script in a production environment
    load_dotenv()
    client = Client(
       bearer_auth_credentials=BearerAuthCredentials(
        access_token=os.environ['SQUARE_ACCESS_TOKEN']
    ),
        environment=os.environ["SQUARE_ENVIRONMENT"],
    )
    # Use the main location of the account - retrieve_location('yourOtherLocationId') to use a different location
    result = client.locations.retrieve_location('main') #os.environ["SQUARE_LOCATION_ID"]
    location_id = result.body["location"]["id"]


    # Get start and end dates for the sales report
    parser = argparse.ArgumentParser(
        description="Generate a sales report for a time period"
    )
    parser.add_argument(
        "--start-date", required=False, help="Start date for the report, in RFC 3339 format"
    )
    parser.add_argument(
        "--end-date", required=False, help="End date for the report, in RFC 3339 format"
    )
    args = parser.parse_args()

    # If no dates are provided, default to today
    if (not args.start_date or not args.end_date):
        current_date = datetime.datetime.now()
        start_date = current_date.strftime("%Y-%m-%d")
        end_date = (current_date + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        start_date = check_date_format(args.start_date)
        end_date = check_date_format(args.end_date)
        if end_date < start_date:
            print("End date cannot be earlier than start date")

    item_tally = defaultdict(lambda: {"qtySold": 0, "total_sales": 0})
    item_ids = []  # Keep track of item ids for bulk retrieval
    get_orders()
    print_sales_report()
    write_sales_to_csv()
