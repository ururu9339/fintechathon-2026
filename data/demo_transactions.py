import numpy as np
import pandas as pd
from faker import Faker
from datetime import timedelta, date
import random
import json

randomCustomers = pd.DataFrame(columns = ["Name", "IssuedDate", "ActualDate", "TransactionID", "Category", "CashInflow", "CashOutflow", "Status"])

fake = Faker('id_ID')

statuses = ["Accepted", "Pending"]
categories = ["B2B_Sales", "B2C_Sales", "Supplier", "SST", "EPF"]

def generate_customers(num_customers, initial_balance = 50000.0):
    records = []
    for i in range(1, num_customers + 1):
        issued_date = fake.date_between(start_date = "-1y", end_date = "+4w")
        category = random.choice(categories)

        cash_in = 0.0
        cash_out = 0.0

        if category in ["B2B_Sales", "B2C_Sales"]:
            cash_in = round(random.uniform(500, 4500), 2)
            if category == "B2B_Sales":
                actual_date = issued_date + timedelta(days = 65)
                status = "Pending" if actual_date > date.today() else "Accepted"
            else:
                actual_date = issued_date
                status = "Accepted"
        else: 
            cash_out = round(random.uniform(200, 1500), 2)
            actual_date = issued_date + timedelta(days = random.randint(1, 5))
            status = "Accepted"
            
        records.append({
            "Name": fake.company() if category != "B2C_Sales" else "Walk-in Customer",
            "IssuedDate": issued_date,
            "ActualDate": actual_date,
            "TransactionID": f"TN-{i:04d}",
            "Category": category, 
            "CashInflow": cash_in,
            "CashOutflow": cash_out,
            "Status": status
        })
    df = pd.DataFrame(records)

    df = df.sort_values(by = "ActualDate").reset_index(drop = True)
    df["NetMovement"] = df["CashInflow"] - df["CashOutflow"]
    df["CurrentBankAccount"] = initial_balance
    df.loc[df["Status"] == "Accepted", "CurrentBankAccount"] = initial_balance + df.loc[df["Status"] == "Accepted", "NetMovement"].cumsum()

    return df

df_transactions = generate_customers(300)

if __name__ == "__main__":
    print(df_transactions)
