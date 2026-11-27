"""User-facing text of the page: one place to read and to refer to from tests."""

PAGE_TITLE = "Grammar corrector"
TITLE = f"# {PAGE_TITLE}"
DESCRIPTION = (
    "Paste a text and get it back with spelling and grammar fixed, in the same language. "
    "It uses a language model on Groq. Your API key is used for this one request and is not stored."
)
KEY_LABEL = "Groq API key"
KEY_URL = "https://console.groq.com/keys"
KEY_INFO = f"Don't have one? [Get a free key]({KEY_URL})."
INPUT_LABEL = "Text to correct"
OUTPUT_LABEL = "Corrected text"
BUTTON_LABEL = "Correct"
EXAMPLES = [
    ["I has a apple and she don't likes it."],
    ["Вчора ми ходили в магазін і купили багато продуктов."],
    ["Their going to the libary tomorow, but its closed on sundays."],
]

MSG_ENTER_KEY = "Enter your Groq API key first."
MSG_CHECK_KEY = "Check your Groq API key."
MSG_EMPTY_INPUT = "Enter some text first."
MSG_TOO_LONG = "The text is too long; shorten it."
MSG_RATE_LIMITED = "Groq rate limit reached; wait a minute and retry."
MSG_PROVIDER_ERROR = "Groq had a problem; try again."
MSG_PROVIDER_TIMEOUT = "Groq took too long; try again."
MSG_GENERIC = "Something went wrong; please try again."

# Backend error `code` -> message; any other code falls back to MSG_GENERIC.
ERROR_MESSAGES = {
    "missing_api_key": MSG_CHECK_KEY,
    "invalid_api_key": MSG_CHECK_KEY,
    "empty_input": MSG_EMPTY_INPUT,
    "input_too_long": MSG_TOO_LONG,
    "rate_limited": MSG_RATE_LIMITED,
    "provider_error": MSG_PROVIDER_ERROR,
    "provider_timeout": MSG_PROVIDER_TIMEOUT,
}
