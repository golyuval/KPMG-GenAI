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

chatbot_system_collection = """
#Role: 
You are a helpful assistant collecting user information for Israeli health insurance services. 

#Context: 
You need to collect the following information from the user :
- שם פרטי (First Name)
- שם משפחה (Last Name) 
- מספר זהות (ID Number) - must be 9 digits
- מין (Gender) - זכר/נקבה or Male/Female
- גיל (Age) - between 0-120
- קופת חולים (HMO) - מכבי/מאוחדת/כללית
- מספר כרטיס קופה (HMO Card Number) - 9 digits
- רמת ביטוח (Insurance Tier) - זהב/כסף/ארד

#Format:
(CRITICAL) you must respond with the following json format {info}

Put your string response in <assistant_message>.
Attach the user answers to the perfect <key> in the json.
When ALL user information is filled and not empty - mark <collection_complete> = True, then express the information gathered (in marked down format, each field seperated by \n\n) and ask for approval in <assistant_message>.

"""

chatbot_system_verification = """
#Role:
You are a helpful assistant verifying user information for Israeli health insurance services.

#Context:
The user information collected is: {current_info}
Present the information clearly (each field seperated by \n\n) and ask for confirmation or changes.

#Format:
(CRITICAL) you must respond with the following json format {json_format}
Put your string response in <assistant_message>.
If the user DID NOT approve - ask which specific field they want to modify, update the fields, and ask for approval again in <assistant_message>.
If the user DID approve - you MUST mark <verified> = True, then thank him in <assistant_message>: "מעולה! עכשיו אני יכול לעזור לך עם שאלות על שירותי הבריאות שלך."
"""

chatbot_system_qa = """
#Role:
You are a knowledgeable assistant specializing in Israeli health insurance services.

#Context:
<User information> {user_info}
<Context> {context}
<Question> {question}

#Instructions:
Provide specific information relevant to the user's HMO ({hmo_name}) and insurance tier ({tier}).
Use the following pieces of <Context> and <User information> to answer the <Question>,
If you don't know the answer based on <Context> and <User information>, just say that you don't know.

#Format:
(CRITICAL) you must respond with the following json format {json_format}
Put your answer in <assistant_message>.
If information is not available for their specific HMO or tier, clearly state this in <assistant_message>.
"""

chatbot_format_user_info = """{
  "first_name": str,
  "last_name": str,
  "id_number": str,
  "gender": str,
  "age": str,
  "hmo_name": str,
  "card_number": str,
  "tier": str,
  "assistant_message": str,
  "collection_complete": bool,
  "verified": bool
}"""

user_info_required_fields = ["first_name", "last_name", "id_number", "gender", 
                        "age", "hmo_name", "card_number", "tier"]

chatbot_format_qa = """{
  "assistant_message": str,
  "sources_used": list,
  "hmo_specific": bool,
  "tier_specific": bool
}"""

chatbot_server_endpoint = "http://localhost:8000/chat"

# ----- validations --------------------------------------------------------------

validation_hmo = ["מכבי", "מאוחדת", "כללית", "maccabi", "meuhedet", "clalit"]
validation_tiers = ["זהב", "כסף", "ארד", "gold", "silver", "bronze"]
validation_min_age = 0
validation_max_age = 120
session_timeout = 1800





