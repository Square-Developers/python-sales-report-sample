#! /opt/homebrew/bin/python3

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

import argparse, json, os, sys, uuid
import datetime

from dotenv import load_dotenv
from faker import Faker
from square.client import Client
from square.http.auth.o_auth_2 import BearerAuthCredentials


# Faker generates some of the elements in the seed data
fake = Faker()

# Tags that help identify the seed data (and let us clear it later)
SEED_DATA_REFERENCE_ID = "SEED_DATA"
SKU_PREFIX = SEED_DATA_REFERENCE_ID + "_"


# Upload sample catalog data
def seed_catalog():
    # Read data from external file
    with open("seed-data-catalog.json", "r") as test_data:
        seed_data = json.load(test_data)

    # Add tags to each item, to mark it as seed data
    for x in range(0, len(seed_data["catalog"])):
        if seed_data["catalog"][x]["type"] == "ITEM":
            for y in range(0, len(seed_data["catalog"][x]["item_data"]["variations"])):
                sku = (
                    SKU_PREFIX
                    + seed_data["catalog"][x]["item_data"]["variations"][y][
                        "item_variation_data"
                    ]["sku"]
                )
                seed_data["catalog"][x]["item_data"]["variations"][y][
                    "item_variation_data"
                ]["sku"] = sku

    # Now upload the data
    try:
        result = client.catalog.batch_upsert_catalog_objects(
            body={
                "idempotency_key": str(uuid.uuid4()),
                "batches": [{"objects": seed_data["catalog"]}],
            }
        )
        print("Successfully created catalog")
    except Exception:
        handle_error("Seed catalog", result.errors)


# Upload sample customer data
def seed_customers():
    # Read data from external file
    with open("seed-data-customers.json", "r") as test_data:
        seed_data = json.load(test_data)
    
    customers = dict()
    # Add tags to each item, to mark it as seed data
    for customer in seed_data["customers"]:
        customer["reference_id"] = SEED_DATA_REFERENCE_ID
        customer["email_address"] = fake.email()
        customers['#' + fake.iana_id()] = customer
        # Now upload the data
    try:
        result = client.customers.bulk_create_customers(
            body= {
                "customers": customers
            }
        )
        print("Successfully created customers")
    
    # In case of errors with CreateCustomer...
    except Exception:
        handle_error("Seed customers", result.errors)


# Generate sample inventory data, based on catalog objects
def seed_inventory():
    # Find all the catalog items that we've seeded previously
    result = client.catalog.search_catalog_objects(
        body={
            "object_types": ["ITEM_VARIATION"],
            "query": {
                "prefix_query": {
                    "attribute_name": "sku",
                    "attribute_prefix": SKU_PREFIX,
                }
            },
        }
    )

    # Generate a (fake) inventory count for each item
    changes = []
    for x in result.body["objects"]:
        changes.append ({
            "physical_count": {
                "quantity": str(fake.random_int(min=50, max=100)),
                "location_id": location_id,
                "state": "IN_STOCK",
                "catalog_object_id": x["id"],
                "occurred_at": datetime.datetime.now(datetime.timezone.utc)
            },
            "type": "PHYSICAL_COUNT",      
          }
        )
        
    try:
        client.inventory.batch_change_inventory({
            "idempotency_key": str(uuid.uuid4()),
            "changes": changes
        })
        print("Successfully adjusted inventory for item variations")

    # In case of errors with BatchChangeInventory...
    except Exception:
        handle_error("Seed inventory", result.errors)


# Generate sample order data, based on catalog objects
def seed_orders():
    # Find all the catalog items that we've seeded previously
    result = client.catalog.search_catalog_objects(
        body={
            "object_types": ["ITEM_VARIATION"],
            "query": {
                "prefix_query": {
                    "attribute_name": "sku",
                    "attribute_prefix": SKU_PREFIX,
                }
            },
        }
    )

    # Create an order for each item, varying the line item quantity for each
    print("Creating " + str(len(result.body["objects"])) + " orders and paying for them...")
    for x in result.body["objects"]:
        # Increase the number of orders by changing the range value, currently we will create 1 order for every item variation
        for _ in range(0, 1):
            try:
                result = client.orders.create_order(
                    body={
                        "order": {
                            "location_id": location_id,
                            "line_items": [
                                {
                                    "catalog_object_id": x["id"],
                                    "quantity": str(fake.random_int(min=1, max=5)),
                                    "base_price_money": {
                                        "amount": x["item_variation_data"]["price_money"]["amount"],
                                        "currency": "USD"
                                    }
                                }
                            ],
                            "source": {"name": SEED_DATA_REFERENCE_ID}
                        }
                    }
                )

                # A sale happens when a order is paid for, so generate a payment for each order
                client.payments.create_payment(
                    body={
                        "order_id": result.body["order"]["id"],
                        "idempotency_key": str(uuid.uuid4()),
                        "source_id": "CASH",
                        "amount_money": result.body["order"]["net_amount_due_money"],
                        "cash_details": {
                            "buyer_supplied_money": result.body["order"][
                                "net_amount_due_money"
                            ]
                        },
                    }
                )

            # In case of errors with CreateOrder...
            except Exception:
                handle_error("Seed orders", result.errors)


# Clear sample customer data (delete it)
def clear_customers():
    try:
        # Find all of the seed data for customers
        search_result = client.customers.search_customers(
            body={
                "query": {"filter": {"reference_id": {"exact": SEED_DATA_REFERENCE_ID}}}
            }
        )
        if search_result.is_success():
            if "customers" in search_result.body:
                customer_ids = [obj['id'] for obj in search_result.body['customers']]
                delete_result = client.customers.bulk_delete_customers(
                    body={
                        "customer_ids": customer_ids
                    }
                )
                if delete_result.is_success():
                    print("Successfully cleared customers")
                else:
                    handle_error("Bulk delete customers", delete_result.errors)
            else:
                print("No customers found")
        else:
            handle_error("Search customers", search_result.errors)

    except Exception as e:
        handle_error("Clear customers", str(e))


# Clear sample catalog data (delete it)
def clear_catalog():
    try:
        # Find all of the seed data for catalog objects
        result = client.catalog.search_catalog_objects(body = {
            "object_types": [
                "ITEM_VARIATION"
           ],
            'query': {
                'prefix_query': {
                    'attribute_name': 'sku',
                    'attribute_prefix': SKU_PREFIX
                }
            }
        })
        
        # Delete each matching catalog object
        if "objects" in result.body:
            ids = []
            item_ids = []

            for x in result.body["objects"]:
                ids.append(x["id"])
                item_ids.append(x["item_variation_data"]["item_id"])

            # delete the item variation data
            client.catalog.batch_delete_catalog_objects(
                body={"object_ids": ids}
            )
            # delete the item data
            client.catalog.batch_delete_catalog_objects(
                body={"object_ids": item_ids}
            )

            print("Successfully cleared catalog")
        else:
            print("No catalog items to delete")

    # In case of errors with SearchCatalogObjects...
    except Exception:
        handle_error("Clear catalog", result.errors)


# Clear sample order data (orders can't be deleted, but they can be canceled)
def clear_orders():
    try:
        # Find all of the seeded orders that are still open (if any)
        result = client.orders.search_orders(
            body={
                "location_ids": [location_id],
                "query": {
                    "filter": {
                        "source_filter": {"source_names": [SEED_DATA_REFERENCE_ID]},
                        "state_filter": {"states": ["OPEN","DRAFT"]},
                    }
                },
            }
        )
    # In case of errors with SearchOrders...
    except Exception:
        handle_error("Clear orders", result.errors)
        
    # Cancel them
    if "orders" in result.body:
        for x in result.body["orders"]:
            result = client.orders.update_order(
                order_id=x["id"],
                body={"order": {"state": "CANCELED", "version": x["version"]}},
            )
            if result.is_success():
                print("Order " + x["id"] + " canceled")
            else:
                print (result.errors[0]['detail'])
                
    else:
        print("No orders to cancel")



# Error handler
def handle_error(function: str, errors):
    print("Exception,  " + function)
    for err in errors:
        print(f"\tcategory: {err['category']}")
        print(f"\tcode: {err['code']}")
        print(f"\tdetail: {err['detail']}")
    sys.exit(1)


if __name__ == "__main__":
    load_dotenv()

    # We don't recommend running this script in a production environment
    if os.environ['SQUARE_ENVIRONMENT'] != "sandbox":
        print("This script is intended for use with the Square Sandbox environment. Do not run this script in a production environment.")
        sys.exit(1)

    client = Client(
       bearer_auth_credentials=BearerAuthCredentials(
        access_token=os.environ['SQUARE_ACCESS_TOKEN']
    ),
        environment=os.environ["SQUARE_ENVIRONMENT"],
    )


    # Use the main location of the account - retrieve_location('yourOtherLocationId') to use a different location
    result = client.locations.retrieve_location('main')
    location_id = result.body["location"]["id"]

    # Determine whether we're creating or clearing test data
    parser = argparse.ArgumentParser(
        description="Upload or remove test data",
        epilog="You can specify either --seed or --clear, but not both",
    )
    parser.add_argument("--seed", action="store_true", help="Upload test data")
    parser.add_argument("--clear", action="store_true", help="Remove test data")

    args = parser.parse_args()

    if args.seed and not args.clear:
        seed_customers()
        seed_catalog()
        seed_inventory()
        seed_orders()
        print("Seed data upload complete.")
    elif args.clear and not args.seed:
        if (input("Are you sure? (y/N): ").lower()) == "y":
            clear_customers()
            clear_catalog()
            # Note that inventory data persists and can't be deleted, or otherwise "cleared"
            # Note that completed orders can't be deleted - open or draft orders may be canceled
            clear_orders()
    else:
        parser.print_usage()
