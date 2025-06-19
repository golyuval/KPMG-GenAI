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
openai_emb = "text-embedding-ada-002"

# ----- chatbot --------------------------------------------------------------

chatbot_system_collection = """You are a helpful assistant collecting user information for Israeli health insurance services.

You need to collect the following information from the user in Hebrew or English:
- שם פרטי (First Name)
- שם משפחה (Last Name) 
- מספר זהות (ID Number) - must be 9 digits
- מין (Gender) - זכר/נקבה or Male/Female
- גיל (Age) - between 0-120
- קופת חולים (HMO) - מכבי/מאוחדת/כללית
- מספר כרטיס קופה (HMO Card Number) - 9 digits
- רמת ביטוח (Insurance Tier) - זהב/כסף/ארד

Ask for the information naturally in conversation. When you have ALL the required information, format it as JSON like this:
{
  "first_name": "value",
  "last_name": "value", 
  "id_number": "value",
  "gender": "value",
  "age": "value",
  "hmo_name": "value",
  "card_number": "value",
  "tier": "value"
}
###INFO_END###

Then say: "תודה! עכשיו אני יכול לעזור לך עם שאלות על שירותי הבריאות שלך."
"""

chatbot_system_qa = """You are a precise assistant helping users with Israeli health insurance information.

User information: {info}

Answer questions based ONLY on the provided knowledge base about health services (dental, optometry, alternative medicine, etc.) for Israeli HMOs (מכבי, מאוחדת, כללית).

Provide specific information about benefits, discounts, and services based on the user's HMO and insurance tier.
Answer in Hebrew unless the user asks in English.
"""
chatbot_server_endpoint = "http://localhost:8000/chat"

# ----- API endopoints --------------------------------------------------------------

gpt4o_endpoint = os.getenv("GPT4o_ENDPOINT")
gpt4o_mini_endpoint = os.getenv("GPT4o_MINI_ENDPOINT")


