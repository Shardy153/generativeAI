import openai
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Get tokens from environment
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")

# Validate required environment variables
if not LLM_ENDPOINT:
    print("Error: SLACK_BOT_TOKEN environment variable is not set")
    sys.exit(1)

if not LLM_API_KEY:
    print("Error: SLACK_APP_TOKEN environment variable is not set")
    sys.exit(1)

def llm_client():
    client = openai.OpenAI(
        api_key=LLM_API_KEY,
        base_url=LLM_ENDPOINT 
    )
    return client

def chat(client,text):
    response = client.chat.completions.create(
        model=LLM_MODEL, # model to send to the proxy
        messages = [
            {
                "role": "user",
                "content": text
            }
        ]
    )    
    response = response.to_dict()
    response = response["choices"][0]["message"]["content"]
    return response
