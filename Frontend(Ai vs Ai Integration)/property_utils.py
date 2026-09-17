import re
from typing import Any, Dict, List, Optional


SCENARIOS = {
    1: "Land / Plot",
    2: "Apartment / Flat",
    3: "Villa / Independent House"
}


LAND_TITLE_PATTERNS = [
    r"\bplot\b",
    r"\bplots\b",
    r"\bland\b",
    r"\bresidential\s+plot\b",
    r"\bresidential\s+plots\b",
    r"\bopen\s+plot\b",
    r"\bopen\s+plots\b",
    r"\bvacant\s+land\b",
    r"\bvacant\s+plot\b"
]


APARTMENT_TITLE_PATTERNS = [
    r"\bflat\b",
    r"\bflats\b",
    r"\bapartment\b",
    r"\bapartments\b"
]


VILLA_TITLE_PATTERNS = [
    r"\bvilla\b",
    r"\bvillas\b",
    r"\bindependent\s+house\b",
    r"\bindependent\s+houses\b",
    r"\bindependent\s+home\b",
    r"\bindependent\s+homes\b"
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def contains_pattern(text: str, patterns: List[str]) -> bool:
    if not text:
        return False

    return any(
        re.search(pattern, text, re.IGNORECASE)
        for pattern in patterns
    )


def classify_property(
    property_data: Dict[str, Any]
) -> Optional[str]:

    if not isinstance(property_data, dict):
        return None

    name = clean_text(property_data.get("Name"))
    title = clean_text(property_data.get("Property Title"))
    description = clean_text(property_data.get("Description"))

    # Property Title has highest priority
    if contains_pattern(title, APARTMENT_TITLE_PATTERNS):
        return "apartment"

    if contains_pattern(title, VILLA_TITLE_PATTERNS):
        return "villa"

    if contains_pattern(title, LAND_TITLE_PATTERNS):
        return "land"

    # Description
    if contains_pattern(description, APARTMENT_TITLE_PATTERNS):
        return "apartment"

    if contains_pattern(description, VILLA_TITLE_PATTERNS):
        return "villa"

    if contains_pattern(description, LAND_TITLE_PATTERNS):
        return "land"

    # Name is weak fallback
    if contains_pattern(name, APARTMENT_TITLE_PATTERNS):
        return "apartment"

    if contains_pattern(name, VILLA_TITLE_PATTERNS):
        return "villa"

    if contains_pattern(name, LAND_TITLE_PATTERNS):
        return "land"

    return None


def get_scenario_key(scenario: int) -> str:
    return {
        1: "land",
        2: "apartment",
        3: "villa"
    }[scenario]


def get_filtered_properties(
    dataset,
    scenario: int
) -> List[Dict[str, Any]]:

    if dataset is None:
        return []

    if hasattr(dataset, "empty") and dataset.empty:
        return []

    if not hasattr(dataset, "empty") and not dataset:
        return []

    scenario_key = get_scenario_key(scenario)
    filtered_properties = []

    if hasattr(dataset, "iloc"):

        for original_index in range(len(dataset)):

            property_data = (
                dataset.iloc[original_index].to_dict()
            )

            if classify_property(property_data) == scenario_key:

                filtered_properties.append({
                    "original_dataset_index": original_index,
                    "property": property_data
                })

    else:

        for original_index, property_data in enumerate(dataset):

            if classify_property(property_data) == scenario_key:

                filtered_properties.append({
                    "original_dataset_index": original_index,
                    "property": property_data
                })

    return filtered_properties


def extract_price(
    property_data
) -> Optional[float]:

    if not isinstance(property_data, dict):
        return None

    possible_columns = [
        "Price",
        "price",
        "PRICE",
        "Property Price",
        "property_price"
    ]

    for column in possible_columns:

        if column not in property_data:
            continue

        value = property_data[column]

        if value is None:
            continue

        try:

            value_string = str(value).strip()

            cleaned = (
                value_string
                .replace(",", "")
                .replace("₹", "")
                .replace("Rs.", "")
                .replace("Rs", "")
                .strip()
            )

            lower_value = cleaned.lower()

            if "lakhs" in lower_value:
                number = float(
                    lower_value.replace("lakhs", "").strip()
                )
                return number * 100000

            if "lakh" in lower_value:
                number = float(
                    lower_value.replace("lakh", "").strip()
                )
                return number * 100000

            if lower_value.endswith("l"):
                number = float(lower_value[:-1].strip())
                return number * 100000

            if "crores" in lower_value:
                number = float(
                    lower_value.replace("crores", "").strip()
                )
                return number * 10000000

            if "crore" in lower_value:
                number = float(
                    lower_value.replace("crore", "").strip()
                )
                return number * 10000000

            if lower_value.endswith("cr"):
                number = float(lower_value[:-2].strip())
                return number * 10000000

            number = float(cleaned)

            if number < 10000:
                return number * 100000

            return number

        except Exception:
            continue

    return None