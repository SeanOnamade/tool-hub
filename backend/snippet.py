import openai
import os
# this snippet is just to test the openai api key and connection
# had to pay like $10

openai.api_key = os.getenv("OPENAI_API_KEY")

try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # Use GPT-3.5-turbo cause GPT4 isn't available
        messages=[
            {"role": "system", "content": "You are an API documentation assistant."},
            {"role": "user", "content": "Hello, world!"}
        ]
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error: {e}")
