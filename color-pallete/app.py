from flask import Flask, render_template, request
from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import json 

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
AZURE_ENDPOINT =  os.getenv("OPENAI_ENDPOINT")
client = AzureOpenAI(
		api_version = "",
		api_key = API_KEY,
		azure_endpoint = AZURE_ENDPOINT)

def get_colors(prompt):
	messages=[
    	{"role": "assistant", 
    	"content": f"""You are a colour pallete generating assistant that responds with a text prompts for colour palettes.
    	You should generate colour that fits the theme or mood of the promt, colour list ranging from 2 to 8.
    	Desired Format: Only want a array of hexadeciaml colour codes, no extra text, not even json.
        
    	Text: {prompt}.
    	JSON Array:"""},    
      ]
	response = client.chat.completions.create(
		messages = messages,
		model = "gpt-4o-mini")
	response = response.to_dict()
	response = response["choices"][0]["message"]["content"]
	response = response.strip('[]').split(', ')
	return response


app = Flask(__name__, template_folder="templates", static_url_path="", static_folder="static")


@app.route("/palette", methods=["POST"])
def prompt():
	query = request.form.get("query")
	colors = get_colors(query)
	return {"colors" : colors}


@app.route("/")
def index():
	return render_template("index.html")
	
if __name__ == "__main__":
	app.run(debug=True)	