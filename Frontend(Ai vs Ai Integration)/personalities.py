# personalities.py

PERSONALITIES = {
    1: {
        "name": "Aggressive",
        "description": (
            "Firm bargaining personality. "
            "Makes strong offers and tries to maximize its advantage."
        )
    },

    2: {
        "name": "Collaborative",
        "description": (
            "Cooperative negotiation personality. "
            "Tries to understand the other side, "
            "makes reasonable concessions, "
            "and focuses on a mutually beneficial agreement."
        )
    },

    3: {
        "name": "Risk-Averse",
        "description": (
            "Careful negotiation personality. "
            "Avoids risky offers and prefers safe and reasonable deals."
        )
    }
}


def display_personalities(role):
    print("\n===================================")
    print(f"SELECT {role.upper()} PERSONALITY")
    print("===================================")

    for number, data in PERSONALITIES.items():
        print(f"{number}. {data['name']}")


def get_personality(choice):
    return PERSONALITIES.get(choice)