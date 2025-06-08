import os
from dotenv import load_dotenv
from openai import AzureOpenAI

# Load environment variables
load_dotenv()

# Retrieve credentials from environment
api_key = os.getenv('OPENAI_API_KEY')
openai_endpoint = os.getenv('OPENAI_ENDPOINT')

# Chat history
previous_questions = []
previous_answers = []

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=api_key,
    azure_endpoint=openai_endpoint,
    api_version="2024-02-15-preview"  # Update with correct version
)

def ask_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    """Send prompt to Azure OpenAI and return the response."""
    messages = [
        {"role": "user", "content": prompt}
    ]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        n=1
    )
    return response.choices[0].message.content.strip()

# Main Chat Loop
print("🤖 Welcome to the Azure OpenAI ChatBot! Type 'exit' to quit.")

while True:
    user_input = input("\nYou: ").strip()
    
    if user_input.lower() == "exit":
        print("👋 Goodbye!")
        break

    # Build chat history to simulate context
    history = ""
    for q, a in zip(previous_questions, previous_answers):
        history += f"The user asks: {q}\n"
        history += f"OPENAI answers: {a}\n"

    history += f"The user asks: {user_input}\n"

    # Get response from OpenAI
    answer = ask_openai(history)
    print(f"\nOPENAI: {answer}")

    # Store Q&A for context in next turn
    previous_questions.append(user_input)
    previous_answers.append(answer)
