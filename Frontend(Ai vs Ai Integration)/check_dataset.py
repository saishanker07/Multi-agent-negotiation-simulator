import pandas as pd

FILE_NAME = "dataset_real.csv"

try:
    df = pd.read_csv(FILE_NAME)

    print("\n===================================")
    print("       DATASET INFORMATION")
    print("===================================\n")

    print("Number of rows:", len(df))
    print("Number of columns:", len(df.columns))

    print("\nColumns:")
    for column in df.columns:
        print("-", column)

    print("\nFirst 5 records:")
    print(df.head())

except FileNotFoundError:
    print("ERROR: dataset.csv was not found.")
    print("Make sure dataset.csv is inside the project folder.")

except Exception as e:
    print("ERROR:", e)