import os
from typing import Final, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

# Load Google API Key and (optional) model names
load_dotenv()
GOOGLE_API_KEY: Final[Optional[str]] = os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL: Final[str] = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
# Used when the main model is overloaded or rate limited
GEMINI_FALLBACK_MODEL: Final[str] = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-flash-lite-latest")

# "Busy" errors worth retrying: rate limited, server error, overloaded, timed out
RETRY_STATUS_CODES: Final[List[int]] = [429, 500, 503, 504]

class GeminiChat:
    def __init__(self,
                 api_key: str,
                 name: str = "Daisy the Discord Chatbot",
                 model_name: str = GEMINI_MODEL,
                 fallback_model_name: str = GEMINI_FALLBACK_MODEL) -> None:
        # Initialize Google Gemini, retrying busy errors a few times before giving up
        self._name = name
        self._model_name = model_name
        self._fallback_model_name = fallback_model_name
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=20_000, # milliseconds per request, so a stuck request can't hang the bot
                retry_options=types.HttpRetryOptions(
                    attempts=2,
                    initial_delay=1.0,
                    max_delay=8.0,
                    http_status_codes=RETRY_STATUS_CODES,
                )
            ),
        )
        self.set_name(name)

    async def get_response(self, user_input: str) -> str:
        try:
            response = await self.chat.send_message(user_input)
        except Exception as e:
            # Errors like a bad API key won't be fixed by another model
            if isinstance(e, errors.APIError) and e.code not in RETRY_STATUS_CODES:
                print("Gemini API error: ", e)
                return "No response from Gemini API: " + repr(e)
            # Busy or timed out: let the fallback model answer instead
            print(f"{self._model_name} failed ({e!r}), trying {self._fallback_model_name}")
            try:
                response = await self._ask_fallback(user_input)
            except Exception as fallback_error:
                print("Gemini API error: ", fallback_error)
                return "Gemini is very busy right now. Please try again in a minute."
        return response.text or "(Gemini returned an empty response.)"

    async def _ask_fallback(self, user_input: str) -> types.GenerateContentResponse:
        '''
        Answer with the fallback model, then carry the conversation back to the
        main model so the next message tries it first.
        '''
        fallback_chat = self._new_chat(self._fallback_model_name, self.chat.get_history())
        response = await fallback_chat.send_message(user_input)
        self.chat = self._new_chat(self._model_name, fallback_chat.get_history())
        return response

    def clear_history(self) -> None:
        self.set_name(self._name)

    def get_history(self) -> List[types.Content]:
        return self.chat.get_history()

    def set_name(self, name: str) -> None:
        '''
        Give the bot a name and start a fresh conversation.
        '''
        self._name: str = name
        self.chat = self._new_chat(self._model_name)

    def _new_chat(self, model_name: str, history: Optional[List[types.Content]] = None):
        name_instructions: str = f"You are a friendly Discord chatbot named '{self._name}'. \
Do not reveal that you were created by Google or any other identifying names \
such as Bard, Gemini, etc. Keep replies short enough for a Discord message."
        return self.client.aio.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(system_instruction=name_instructions),
            history=history or [],
        )
