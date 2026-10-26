from typing import Optional

import discord

from gemini_chat import GOOGLE_API_KEY, GeminiChat

# Discord rejects messages longer than 2000 characters
MAX_MESSAGE_LENGTH: int = 2000


class DiscordClient(discord.Client):
    async def setup_hook(self) -> None:
        '''
        Runs once before the bot connects. Set up Google Gemini here so a
        reconnect doesn't reset the chat.
        '''
        self.listen: bool = True
        self.model: Optional[GeminiChat] = None

        if GOOGLE_API_KEY:
            try:
                self.model = GeminiChat(GOOGLE_API_KEY)
                print("Gemini is Ready!")
            except Exception as e:
                print(f"Error initializing Gemini: {e}")
        else:
            print("Google API Key missing!")

    async def on_ready(self) -> None:
        '''
        Once the bot is ready, print the status of the bot.
        '''
        print(f"{self.user} is connected and ready!")

    async def on_message(self, message: discord.Message) -> None:
        '''
        Retrieve message details and act accordingly
        '''
        # If the message author is the bot, do nothing (e.g. return None)
        if message.author == self.user:
          return

        print(f"[{message.channel}] {message.author}: {message.content}")

        await self.send_message(message)

    async def send_message(self, message: discord.Message) -> None:
        '''
        Send a response back to the user from user's message.
        '''
        user_message: str = message.content

        if not user_message:
            print('Message was empty because intents were probably not enabled')
            return

        # If the first character of the message is '?', set flag that the message
        # response should be a DM
        is_private: bool = user_message[0] == '?'
        if is_private:
            user_message = user_message[1:] # remove '?' from the message
            message_channel = message.author
        else:
            message_channel = message.channel

        if self.model is None:
            await message_channel.send("Gemini isn't set up. Check the GOOGLE_API_KEY in .env.")
            return

        if user_message.startswith("\\set_name "):
            if len(user_message[10:]) > 25:
                await message_channel.send("Name cannot be longer than 25 characters.")
            else:
                self.model.set_name(user_message[10:].strip())
                send_message: str = f"Name set to {self.model._name}. Chat history reset."
                await message_channel.send(send_message)
        elif user_message.startswith("\\stop_listening"):
            self.listen = False
            await message_channel.send("Gemini listening stopped.")
        elif user_message.startswith("\\listen"):
            self.listen = True
            await message_channel.send("Gemini listening started.")
        elif user_message.startswith("\\get_history"):
            history = self.model.get_history()
            lines = [f"{c.role}: {''.join(p.text or '' for p in c.parts or [])}" for c in history]
            await send_long(message_channel, "\n".join(lines) or "No chat history yet.")
        else:
            if self.listen:
                async with message_channel.typing():
                    response = await self.model.get_response(user_message)
                await send_long(message_channel, response)
            else:
                return


async def send_long(channel: discord.abc.Messageable, text: str) -> None:
    '''
    Send text in pieces that fit Discord's message length limit.
    '''
    for start in range(0, len(text), MAX_MESSAGE_LENGTH):
        await channel.send(text[start:start + MAX_MESSAGE_LENGTH])

# Setup bot
intents: discord.Intents = discord.Intents.default()
intents.message_content = True
client: DiscordClient = DiscordClient(intents=intents)
