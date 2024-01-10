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
from dotenv import load_dotenv


# Process all the orders between start_date and end_date
def get_orders():
    limit = 25  # max number of orders per page

    print("Retrieving orders from ", start_date, " to ", end_date)

    # Get the first page of orders
    result = client.orders.search_orders(
        body={
            "location_ids": [location_id],
            "limit": limit,
            "query": {
                "filter": {
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
                print("Order ID: " + order["id"] + ", closed at: " + order["closed_at"])

                # Get basic for this order's items, and save it to the item_tally
                if "line_items" in order:
                    for line_item in order["line_items"]:
                        if "name" in line_item:
                            print(
                                "\t",
                                line_item["name"],
                                "-",
                                line_item["variation_name"],
                                "(qty:",
                                line_item["quantity"],
                                ")",
                            )
                        else:
                            print("This line item doesn't have a name")

                        # Get basic info about a particular item, and save it to the item_tally
                        if "catalog_object_id" in line_item:
                            item_id = line_item["catalog_object_id"]
                            if not item_id in item_tally:
                                item_tally.update(
                                    {item_id: {"qtySold": int(line_item["quantity"])}}
                                )
                            else:
                                item_tally.update(
                                    {
                                        item_id: {
                                            "qtySold": int(
                                                item_tally[item_id].get("qtySold")
                                            )
                                            + int(line_item["quantity"])
                                        }
                                    }
                                )
                            item_tally[item_id]["name"] = line_item["name"]
                            item_tally[item_id]["variation_name"] = line_item[
                                "variation_name"
                            ]

                            # Get more details about this item from the catalog
                            get_catalog_info(item_id)

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

    # In case of errors with SearchOrders...
    elif result.is_error():
        oops(result.errors)


# Look up an item in the catalog, and save it in the item_tally
def get_catalog_info(item_id):
    try:
        result = client.catalog.retrieve_catalog_object(item_id)

        # Fine-grained item details (such as sku and priceEach) are stored within the
        # item variation data.  Save these details in the item_tally.
        if result.is_success():
            sku = result.body["object"]["item_variation_data"].get("sku")
            if sku:
                item_tally[item_id]["sku"] = sku
        else:
            print("This item variation doesn't have a SKU")

        priceEach = result.body["object"]["item_variation_data"].get("price_money")

        if priceEach:
            item_tally[item_id]["priceEach"] = priceEach
        else:
            print("This item variation doesn't have a price")

        # Find out how many of these items we've sold, and how many remain
        get_inventory_count(item_id)

    # In case of errors with RetrieveCatalogObject...
    except Exception:
        oops(result.errors)


# Retrieve quantity info for an item, and save it in the item_tally.
# (Note that Square only keeps track of quantities if track_inventory
# (in the CatalogItemVariation object) is set to true.
def get_inventory_count(item_id):
    try:
        result = client.inventory.retrieve_inventory_count(
            catalog_object_id=item_id,
            location_ids=location_id,
        )
        item_tally[item_id]["qtyRemaining"] = result.body["counts"][0]["quantity"]

    # In case of errors with GetInventoryCount...
    except Exception:
        oops(result.errors)


# Generate the sales report
def print_sales_report():
    print()
    print(f"*** SALES REPORT: {start_date} - {end_date} ***")
    print(
        f'Item{" "*21}SKU{" "*21}Price{" "*6}QtySold{" "*2}TotalSales{" "*4}QtyRemaining'
    )
    print(f'{"-"*100}')

    grand_total = 0

    # Walk through the item_tally and print the details
    for key, value in item_tally.items():
        print(f'{value.get("name")} - {value.get("variation_name"):18} ', end="")
        print(f'{value.get("sku"):18} ', end="")
        print(
            f'{value.get("priceEach").get("amount"):5.2f} {value.get("priceEach").get("currency")} ',
            end="",
        )
        print(f'{value.get("qtySold"):>5} ', end="")
        print(
            f'{value.get("qtySold") * value.get("priceEach").get("amount"):10} {value.get("priceEach").get("currency")} ',
            end="",
        )
        print(f'{value.get("qtyRemaining"):>7}')

        # Calculate the subtotal for this item, and add to the grand_total
        grand_total += value.get("qtySold") * value.get("priceEach").get("amount")

    # Print the bottom line, and we're done
    print(f"\nGrand total sales: {grand_total}")


# Ensure dates are in YYYY-MM-DD format
def check_date_format(dt):
    fmt = "%Y-%m-%d"

    try:
        dt = datetime.datetime.strptime(dt, fmt)
    except ValueError:
        print(dt, ": Invalid date or date format")
        exit(1)

    return dt.strftime(fmt)


# Error handler
def oops(errors):
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
        access_token=os.environ["SQUARE_ACCESS_TOKEN"],
        environment=os.environ["SQUARE_ENVIRONMENT"],
    )
    location_id = os.environ["SQUARE_LOCATION_ID"]

    # Get start and end dates for the sales report
    parser = argparse.ArgumentParser(
        description="Generate a sales report for a time period"
    )
    parser.add_argument(
        "--start-date", required=True, help="Start date for the report, in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end-date", required=True, help="End date for the report, in YYYY-MM-DD format"
    )
    args = parser.parse_args()

    if (not args.start_date and args.end_date) or (
        args.start_date and not args.end_date
    ):
        print("Missing start-date and/or end_date")
        exit(1)

    start_date = check_date_format(args.start_date)
    end_date = check_date_format(args.end_date)
    if end_date < start_date:
        print("End date cannot be earlier than start date")

    item_tally = {}  # keeps track of subtotals, etc. as the program runs
    get_orders()
    print_sales_report()
