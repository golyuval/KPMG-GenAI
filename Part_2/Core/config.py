import os
from dotenv import load_dotenv

load_dotenv()

# ----- Document Intelligence -----------------------------------------------

doc_int_key = os.getenv("AZURE_DOC_INT_KEY")
doc_int_endpoint = os.getenv("AZURE_DOC_INT_ENDPOINT")

# ----- OpenAI --------------------------------------------------------------

openai_key = os.getenv("AZURE_OPENAI_KEY")
openai_version = os.getenv("AZURE_OPENAI_VERSION")
openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
openai_model = "gpt-4o"
openai_model_mini = "gpt-4o-mini"

chatbot_system_collection = "you are a pirate assistant."

chatbot_system_qa = "you are a precise assistant.\n" \
                    "user info : {info}\n"\
                    "answer only with the provided knowledge"

gpt4o_endpoint = os.getenv("GPT4o_ENDPOINT")
gpt4o_mini_endpoint = os.getenv("GPT4o_MINI_ENDPOINT")


