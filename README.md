
# Sales report sample app

- [Sales report sample app](#sales-report-sample-app)
  - [Overview](#overview)
  - [Installation and Usage](#installation-and-usage)
  - [Useful Links](#useful-links)

## Overview

This sample application demonstrates some of the Square API capabilities.  It uses the Square Orders API, Catalog API and Inventory API to:

* Filter order data by time period and completion status.
* Retrieve product catalog data for items that have been purchased.
* Determine the current inventory on hand for an item.

The sample shows how you can use this data to create a sales report.  The report summarizes all of the items sold during a time period, and includes details such as: 
* Item descriptions
* Number of items purchased
* Price per item
* Total sales amount for the item
* Inventory on hand for the item

The sample application includes a script that creates sample customers and catalog data in your Square account Sandbox environment. The script also generates orders and inventory counts based on the uploaded data.

## Installation and Usage
For more information, see [Build a Sales report](https://developer.squareup.com/docs/commerce/scenarios/simple-sales-report) in the Square developer documentation:
* [Step 1: Download and configure the application](https://developer.squareup.com/docs/commerce/scenarios/simple-sales-report#step-1-download-and-configure-the-application)
* [Step 2: Run the data seeding script](https://developer.squareup.com/docs/commerce/scenarios/simple-sales-report#step-2-run-the-data-seeding-script)
* [Step 3: Run the sales reporting script](https://developer.squareup.com/docs/merchants/scenarios/simple-sales-report#step-3-run-the-sales-reporting-script)
* [Step 4 (optional): Clean up](https://developer.squareup.com/docs/commerce/scenarios/simple-sales-report#step-4-optional-clean-up)

## Useful Links
* [Square Python SDK](https://developer.squareup.com/docs/sdks/python)
* [Orders API Overview](https://developer.squareup.com/docs/orders-api/what-it-does)
* [Orders API Reference](https://developer.squareup.com/reference/square/orders-api)
* [Catalog API Overview](https://developer.squareup.com/docs/catalog-api/what-it-does)
* [Catalog API Reference](https://developer.squareup.com/reference/square/catalog-api)
* [Inventory API Overview](https://developer.squareup.com/docs/inventory-api/what-it-does)
* [Inventory API Reference](https://developer.squareup.com/reference/square/inventory-api)
