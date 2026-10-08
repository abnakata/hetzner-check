import os
import requests
from datetime import datetime, timezone

# ============================================================
# CONFIG
# ============================================================

HETZNER_API_TOKEN = os.getenv("HETZNER_API_TOKEN")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_MESSAGE_ID = os.getenv("DISCORD_MESSAGE_ID")

SERVER_TYPE = "cx23"
LOCATION = "hel1"

HETZNER_URL = "https://console.hetzner.com/projects"
ORDER_URL = "https://console.hetzner.com/projects"


# ============================================================
# HETZNER
# ============================================================

def check_availability():
    url = "https://api.hetzner.cloud/v1/server_types"

    headers = {
        "Authorization": f"Bearer {HETZNER_API_TOKEN}"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    for server_type in data["server_types"]:
        if server_type["name"].lower() != SERVER_TYPE:
            continue

        for location in server_type.get("locations", []):
            if location["name"] == LOCATION:
                return location.get("available", False)

    raise RuntimeError(
        f"Could not find {SERVER_TYPE} in {LOCATION}"
    )


# ============================================================
# DISCORD
# ============================================================

def discord_url():
    return f"{DISCORD_WEBHOOK_URL}/messages/{DISCORD_MESSAGE_ID}"


def get_current_message():
    response = requests.get(
        discord_url(),
        timeout=15
    )

    response.raise_for_status()
    return response.json()


def create_message(embed):
    payload = {
        "embeds": [embed],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": "Open Hetzner",
                        "url": ORDER_URL
                    }
                ]
            }
        ]
    }

    response = requests.post(
        DISCORD_WEBHOOK_URL + "?wait=true",
        json=payload,
        timeout=15
    )

    response.raise_for_status()

    message = response.json()

    print("==========================================")
    print("Discord status message created!")
    print("")
    print("MESSAGE ID:")
    print(message["id"])
    print("")
    print("Add this as a GitHub Secret:")
    print("DISCORD_MESSAGE_ID")
    print("==========================================")

    return message["id"]


def update_message(embed, ping=False):
    payload = {
        "content": "@everyone" if ping else "",
        "embeds": [embed],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": "Open Hetzner",
                        "url": ORDER_URL
                    }
                ]
            }
        ],
        "allowed_mentions": {
            "parse": ["everyone"] if ping else []
        }
    }

    response = requests.patch(
        discord_url(),
        json=payload,
        timeout=15
    )

    response.raise_for_status()


def build_embed(available):
    now = datetime.now(timezone.utc)

    if available:
        return {
            "title": "🚨 Hetzner CX23 Stock Monitor",
            "description": "## 🟢 AVAILABLE\n\n**CX23 is currently available in Helsinki.**",
            "color": 0x57F287,
            "fields": [
                {
                    "name": "📍 Location",
                    "value": "**Helsinki** (`hel1`)",
                    "inline": True
                },
                {
                    "name": "🖥️ Server",
                    "value": "**CX23**",
                    "inline": True
                },
                {
                    "name": "🟢 Status",
                    "value": "**AVAILABLE**",
                    "inline": True
                }
            ],
            "footer": {
                "text": "Hetzner Stock Monitor"
            },
            "timestamp": now.isoformat()
        }

    return {
        "title": "🖥️ Hetzner CX23 Stock Monitor",
        "description": "## 🔴 UNAVAILABLE\n\nCX23 is currently not available in Helsinki.",
        "color": 0xED4245,
        "fields": [
            {
                "name": "📍 Location",
                "value": "**Helsinki** (`hel1`)",
                "inline": True
            },
            {
                "name": "🖥️ Server",
                "value": "**CX23**",
                "inline": True
            },
            {
                "name": "🔴 Status",
                "value": "**UNAVAILABLE**",
                "inline": True
            }
        ],
        "footer": {
            "text": "Hetzner Stock Monitor"
        },
        "timestamp": now.isoformat()
    }


# ============================================================
# MAIN
# ============================================================

def main():

    if not HETZNER_API_TOKEN:
        raise RuntimeError("HETZNER_API_TOKEN is not set")

    if not DISCORD_WEBHOOK_URL:
        raise RuntimeError("DISCORD_WEBHOOK_URL is not set")

    available = check_availability()

    print(
        f"CX23 / {LOCATION}: "
        f"{'AVAILABLE' if available else 'UNAVAILABLE'}"
    )

    embed = build_embed(available)

    # --------------------------------------------------------
    # First run: create the permanent Discord status message
    # --------------------------------------------------------

    if not DISCORD_MESSAGE_ID:
        create_message(embed)

        print("")
        print("IMPORTANT:")
        print("Copy the Message ID above into GitHub Secrets as:")
        print("DISCORD_MESSAGE_ID")

        return

    # --------------------------------------------------------
    # Existing message: determine previous status
    # --------------------------------------------------------

    previous_message = get_current_message()

    previous_available = False

    embeds = previous_message.get("embeds", [])

    if embeds:
        description = embeds[0].get("description", "")

        if "🟢 AVAILABLE" in description:
            previous_available = True

    # --------------------------------------------------------
    # Ping only when status changes:
    #
    # UNAVAILABLE -> AVAILABLE
    # --------------------------------------------------------

    became_available = (
        available and not previous_available
    )

    update_message(
        embed,
        ping=became_available
    )

    if became_available:
        print("🚨 CX23 JUST BECAME AVAILABLE!")
        print("Sent @everyone notification.")
    else:
        print("Status updated without notification.")


if __name__ == "__main__":
    main()
