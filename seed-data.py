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
from datetime import datetime

from dotenv import load_dotenv
from faker import Faker
from square.client import Client
# from square import Client

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
        oops("Seed catalog", result.errors)


# Upload sample customer data
def seed_customers():
    # Read data from external file
    with open("seed-data-customers.json", "r") as test_data:
        seed_data = json.load(test_data)

    # Add tags to each item, to mark it as seed data
    for customer in seed_data["customers"]:
        customer["reference_id"] = SEED_DATA_REFERENCE_ID
        customer["email_address"] = fake.email()

        # Now upload the data
        try:
            result = client.customers.create_customer(customer)
            print("Successfully created customer:", result.body["customer"]["id"])
        
        # In case of errors with CreateCustomer...
        except Exception:
            oops("Seed customers", result.errors)


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
    for x in result.body["objects"]:
        try:
            stmp = datetime.now().isoformat()
            result_2 = client.inventory.batch_change_inventory(
                {
                    "idempotency_key": str(uuid.uuid4()),
                    "changes": [
                        {
                            "physical_count": {
                                "quantity": str(fake.random_int(min=100, max=200)),
                                "location_id": location_id,
                                "state": "IN_STOCK",
                                "catalog_object_id": x["id"],
                                "occurred_at": datetime.utcnow().isoformat("T") + "Z",
                            },
                            "type": "PHYSICAL_COUNT",
                        }
                    ],
                }
            )
            print("Successfully adjusted inventory for item variation: " + x["id"])

        # In case of errors with BatchChangeInventory...
        except Exception:
            oops("Seed inventory", result.errors)


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
    for x in result.body["objects"]:
        for y in range(0, fake.random_int(min=1, max=10)):
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
                                        "amount": x["item_variation_data"]["price_money"]["amount"] + int(fake.random_int(min=100, max=5000)),
                                        "currency": "USD"
                                    }
                                }
                            ],
                            "source": {"name": SEED_DATA_REFERENCE_ID}
                        }
                    }
                )
                print("Successfully created order:", \
                      result.body["order"]["id"] + \
                        " Line item base price:", \
                            result.body["order"]["line_items"][0]["base_price_money"]["amount"])

                # A sale happens when a order is paid for, so generate a payment for each order
                result_2 = client.payments.create_payment(
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
                print("\tSuccessfully paid for order: ", result.body["order"]["id"])

            # In case of errors with CreateOrder...
            except Exception:
                oops("Seed orders", result.errors)


# Clear sample customer data (delete it)
def clear_customers():
    try:
        # Find all of the seed data for customers
        result = client.customers.search_customers(
            body={
                "query": {"filter": {"reference_id": {"exact": SEED_DATA_REFERENCE_ID}}}
            }
        )
        if result.is_success():

            # Delete each matching customer
            if "customers" in result.body:
                for c in result.body["customers"]:
                    try:
                        result_2 = client.customers.delete_customer(c["id"])
                        print("Successfully cleared customer:", c["id"])

                    # In case of errors with DeleteCustomer...    
                    except Exception:
                        oops("Clear customers", result_2.errors)
            else:
                print("No customers found")

    # In case of errors with SearchCustomers...        
    except Exception:
        oops("Clear customers", result.errors)


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
            for x in result.body["objects"]:
                ids.append(x["id"])
                result = client.catalog.batch_delete_catalog_objects(
                body={"object_ids": ids}
            )
            print("Successfully cleared catalog")
        else:
            print("No catalog items to delete")

    # In case of errors with SearchCatalogObjects...
    except Exception:
        oops("Clear catalog", result.errors)


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
        oops("Clear orders", result.errors)
        
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
def oops(function: str, errors):
    print("Exception,  " + function)
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
    elif args.clear and not args.seed:
        if (input("Are you sure? (y/n)").lower()) == "y":
            clear_customers()
            clear_catalog()
            # Note that inventory data persists and can't be deleted, or otherwise "cleared"
            clear_orders()
    else:
        parser.print_usage()
