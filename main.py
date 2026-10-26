import os
from typing import Final

from dotenv import load_dotenv

from discord_bot import client

# Load Discord Token and Google API Key
load_dotenv()
DISCORD_TOKEN: Final[str | None] = os.getenv('DISCORD_TOKEN')

def main() -> None:
    # Setup Discord Client
    if DISCORD_TOKEN:
        client.run(token=DISCORD_TOKEN)
    else:
        print("Discord token missing!")

if __name__ == '__main__':
    main()