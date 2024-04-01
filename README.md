
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
### Setup
Create a new Python Virtual Environment and activated it
```
$ python -m venv env
$ source env/bin/activate
```
Install the project dependencies
```
$ pip install -r requirements.txt
```

Rename the file `.env.example` to `.env`
```
$ mv .env.example .env
```
Place the Sandbox access token for your desired Sandbox Test Account as the value of `SQUARE_ACCESS_TOKEN` in your `.env` file.

You can get the Access Token from [here](https://developer.squareup.com/console/en/sandbox-test-accounts)


### Seed Test Data
We have provided a seed script to create catalog items, inventory, customers, and orders into your Sandbox Seller account

**Caution:** This will create some permanent data into your Sandbox test account. We highly recommend creating a new test account and using that for this project.

Run the seed script
```
python ./seed-data.py --seed
```

### Run the sales report

Now that your Sandbox test account has data in it you can run the sales report

```
$ python ./simple-sales-report.py --start-date 2024-01-01 --end-date 2024-12-31
```

We provide a start date and end date, this will grab data for the whole year, but you can change those values to hone in on a specific date range of your choice.

When the script finishes running you will get a table print out of your sales report as well as a newly created `sales_report.csv` file.

### Cleanup (Optional)

If you like, you can clear out the seeded data by running the seed script with the `--clear` flag. 
```
$ python ./seed-data.py --clear
```

This will clear all the catalog items, customers, and any orders in `OPEN` or `DRAFT` status. 

**Note**: Inventory counts and completed orders can't be deleted.


## More Information
[Build a Sales report](https://developer.squareup.com/docs/commerce/scenarios/simple-sales-report) in the Square developer documentation:

## Useful Links
* [Square Python SDK](https://developer.squareup.com/docs/sdks/python)
* [Orders API Overview](https://developer.squareup.com/docs/orders-api/what-it-does)
* [Orders API Reference](https://developer.squareup.com/reference/square/orders-api)
* [Catalog API Overview](https://developer.squareup.com/docs/catalog-api/what-it-does)
* [Catalog API Reference](https://developer.squareup.com/reference/square/catalog-api)
* [Inventory API Overview](https://developer.squareup.com/docs/inventory-api/what-it-does)
* [Inventory API Reference](https://developer.squareup.com/reference/square/inventory-api)
