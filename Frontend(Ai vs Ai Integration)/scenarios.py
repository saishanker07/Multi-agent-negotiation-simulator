# scenarios.py

SCENARIOS = {
    1: {
        "name": "Land / Plot",
        "keywords": ["plot", "land", "site"]
    },

    2: {
        "name": "Apartment / Flat",
        "keywords": ["flat", "apartment", "bhk"]
    },

    3: {
        "name": "Villa / Independent House",
        "keywords": ["villa", "independent house"]
    }
}


def display_scenarios():
    print("\n===================================")
    print("       SELECT SCENARIO")
    print("===================================")

    for number, data in SCENARIOS.items():
        print(f"{number}. {data['name']}")


def get_scenario(choice):
    return SCENARIOS.get(choice)