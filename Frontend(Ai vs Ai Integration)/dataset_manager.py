# dataset_manager.py

import os
import re
import pandas as pd


def load_dataset(filename="dataset.csv"):
    if not os.path.exists(filename):
        raise FileNotFoundError(
            f"Dataset '{filename}' was not found."
        )

    df = pd.read_csv(filename)

    if df.empty:
        raise ValueError("Dataset is empty.")

    print(
        f"\nDataset loaded successfully: "
        f"{len(df)} properties"
    )

    return df


def select_property(df, scenario):
    keywords = scenario["keywords"]

    columns_to_search = [
        "Name",
        "Property Title",
        "Description",
        "Location"
    ]

    available_columns = [
        column
        for column in columns_to_search
        if column in df.columns
    ]

    if not available_columns:
        return df.sample(1).iloc[0]

    combined_text = (
        df[available_columns]
        .fillna("")
        .astype(str)
        .agg(" ".join, axis=1)
        .str.lower()
    )

    mask = combined_text.apply(
        lambda text: any(
            keyword.lower() in text
            for keyword in keywords
        )
    )

    matching = df[mask]

    if matching.empty:
        print(
            "\nNo exact property was found "
            "for this scenario."
        )
        print("Selecting a property from the dataset.")

        return df.sample(1).iloc[0]

    return matching.sample(1).iloc[0]


def get_property_details(row):
    return {
        "name": str(
            row.get(
                "Property Title",
                "Unknown Property"
            )
        ),

        "location": str(
            row.get(
                "Location",
                "Unknown Location"
            )
        ),

        "area": str(
            row.get(
                "Total_Area",
                "Unknown"
            )
        ),

        "price": str(
            row.get(
                "Price",
                "Unknown"
            )
        ),

        "price_per_sqft": str(
            row.get(
                "Price_per_SQFT",
                "Unknown"
            )
        ),

        "description": str(
            row.get(
                "Description",
                ""
            )
        ),

        "baths": str(
            row.get(
                "Baths",
                "Unknown"
            )
        ),

        "balcony": str(
            row.get(
                "Balcony",
                "Unknown"
            )
        )
    }


def extract_price(price_value):
    """
    Convert dataset price into rupees.
    Handles values such as:
    30
    30.00
    30 lakhs
    ₹30 lakhs
    3000000
    """

    if price_value is None:
        return None

    text = str(price_value).lower()
    text = text.replace(",", "").strip()

    lakh_match = re.search(
        r"(\d+(?:\.\d+)?)\s*lakh",
        text
    )

    if lakh_match:
        return float(lakh_match.group(1)) * 100000

    crore_match = re.search(
        r"(\d+(?:\.\d+)?)\s*crore",
        text
    )

    if crore_match:
        return float(crore_match.group(1)) * 10000000

    rupee_match = re.search(
        r"(?:₹|rs\.?|inr)\s*(\d+(?:\.\d+)?)",
        text
    )

    if rupee_match:
        value = float(
            rupee_match.group(1)
        )

        if value < 1000:
            return value * 100000

        return value

    number_match = re.search(
        r"\d+(?:\.\d+)?",
        text
    )

    if number_match:
        value = float(
            number_match.group(0)
        )

        # Dataset commonly represents property
        # prices in lakhs.
        if value < 1000:
            return value * 100000

        return value

    return None