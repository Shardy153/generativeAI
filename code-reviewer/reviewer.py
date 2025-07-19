import os
import json
import argparse
import shutil
import logging
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAIError, AuthenticationError, APIConnectionError


if not os.path.exists("logs"):
    os.makedirs("logs")
    print("Directory logs created.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler("logs/code_reviewer.log")        
    ]
)

logger = logging.getLogger(__name__)

global filecontents, original_contents


PROMPT = """
You are an excellent code reviewer, like GitHub Copilot.

You will receive the contents of a code file as input. Generate a code review for that file and suggest improvements in the following areas:
- Style
- Efficiency
- Exception handling
- Performance
- Documentation
- Readability
- Best practices

Suggest as many changes as you can.

If there are any reputable libraries that could improve the code, suggest them.

Be kind and constructive in your suggestions. Assume I will be replacing the **exact old code with the new one**, so provide complete replacements for changed lines.

If you introduce a try block, you **must** include an appropriate except block as well.

Return the changes in a **valid Python-parsable JSON** format. Each change must include:
- `line_before_code_change`: The line **before** the changed code
- `line_after_code_change`: The line **after** the changed code
- `old_code`: The **exact** old code to be replaced
- `new_code`: The **exact** new code to be inserted
- `explanation`: Reason for the change
- `line_number`: Line number in the original file

### JSON Format:
```json
{
    "1": {
        "line_before_code_change": "<LINE BEFORE THE CODE>",
        "line_after_code_change": "<LINE AFTER THE CODE>",
        "old_code": "<OLD_CODE_WITH_ESCAPED_TABS_AND_NEWLINES>",
        "new_code": "<NEW_CODE_WITH_ESCAPED_TABS_AND_NEWLINES>",
        "explanation": "<REASON>",
        "line_number": <LINE_NUMBER>
    },
    ...
}
````

**Important Notes:**

* Use `\\t` for tabs and `\\n` for newlines.
* Escape all backslashes.
* Do not start any string value with a whitespace.
* Your response should be a **standalone, valid JSON object**, without any commentary or extra text.

### Example Input Code:

```python
import subprocess

output = subprocess.check_output("df -h", shell=True, text=True)
for line in output.splitlines()[1:]:
    line = line.split()
    print(line[4])
    line = line[4][:-1]
    print(line)
    print(int(line))
```

### Example Output:

```json
{
    "1": {
        "line_before_code_change": "",
        "line_after_code_change": "for line in output.splitlines()[1:]:",
        "old_code": "output = subprocess.check_output(\\"df -h\\", shell=True, text=True)",
        "new_code": "import shlex\\n\\ncommand = shlex.split(\\"df -h\\")\\noutput = subprocess.check_output(command, text=True)",
        "explanation": "Using shlex to split the command enhances security by avoiding issues related to shell injection attacks due to the shell=True parameter.",
        "line_number": 3
    },
    ...
}
```

Do not include anything other than the final valid JSON.

"""

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def update_python_file(file_path, updated_code, backup_dir):
	file_path_list = file_path.split(".") 	
	backup_file_path = file_path_list[0] + "-backup." + file_path_list[1] 
	backup_file_path = os.path.join(backup_dir, backup_file_path)
	if not os.path.exists(backup_dir):
		os.makedirs(backup_dir)
		logger.info(f"{backup_dir} Directory created.")
	shutil.copy(file_path, backup_file_path)	
	try:
		with open(file_path, "w") as f:
  			f.write(updated_code)
		print(f"{file_path} updated")	  
		logger.info(f"{file_path} updated")	  
	except Exception as e:
		logger.info(f"Error writing to {file_path}. {str(e)}")  			
		print(f"Error writing to {file_path}. {str(e)}")  			


def update_code(old_code,new_code):
	global filecontents		
	logger.info("DEBUG: Implementing code reviewer's suggestion:")
	logger.info("UPDATED CODE:")	
	filecontents = filecontents.replace(old_code, new_code)
	logger.info(filecontents)
	logger.info("\n")	
	return filecontents
	
	
def modify_code(generated_code_review):	
	logger.info("Here are the following changes:")
	for key, value  in generated_code_review.items():
		print(f"Change: #{key}")
		print(f"line_number: {value['line_number']}")
		print(f"=========")
		print("Explanation: " + color.BOLD + value['explanation'] + color.END)
		print(value["line_before_code_change"])				
		print("- " + color.BOLD + color.RED + value["old_code"] + color.END)		
		print("+ " + color.BOLD + color.GREEN + value["new_code"] + color.END)		
		print(value["line_after_code_change"])
		print("\n")
		ans = input("Do you want to implement this change? (y/N)").strip()
		if ans == 'y' or ans == 'Y':
			print("Suggestion accepted.")
			updated_code = update_code(value["old_code"], value["new_code"])
		elif ans == 'N' or ans == 'n':
			print("Suggestion rejected.")
			logger.info("Suggestion rejected.")
		else:
			print("Invalid response, please type y or N.")			
	logger.info("Fixing indentation of the code...")
	user_prompt = f"""Fix Syntax and indentation of this code : {updated_code}. DO NOT ADD ANY EXTRA INFORMARTION, I JUST NEED THE CODE, NO EXPLAINATION."""
	messages=[    	
		{"role": "user", "content": user_prompt},    	    
  	]
	fixed_code = make_openai_request(messages)			
	fixed_code = fixed_code.replace("```python", "")
	fixed_code = fixed_code.replace("```", "")		
	print("\n=============")
	print("Updated Code after implementing all the suggestions.")
	print("=============\n")	
	print(fixed_code)
	return fixed_code			

		

def code_review(file_path, model, preview, backup_dir):	
	global filecontents, original_contents
	try:
		with open(file_path, "r") as file:
			filecontents = file.read()
	except FileNotFoundError:
		logger.info(f"File: {file_path} not found.")		
		logger.info("ABORTING...!!!")
		exit(1)
	except PermissionError:
		logger.info("Permission denied.")
		logger.info("ABORTING...!!!")
		exit(1)
	except IsADirectoryError:
		logger.info("Expected a file but found a directory.")
		logger.info("ABORTING...!!!")
		exit(1)
	except (IOError, OSError) as e:
		logger.info(f"IO error: {e}")
		logger.info("ABORTING...!!!")
		exit(1)
	except UnicodeDecodeError:
		logger.info("File encoding error.")	
		logger.info("ABORTING...!!!")
		exit(1)

	original_contents = filecontents
	user_prompt = f"Code review for the following file : {filecontents}"
	messages=[
    	{"role": "system", "content": PROMPT},
		{"role": "user", "content": user_prompt},    	    
  	]
	generated_code_review = make_openai_request(messages)	
	generated_code_review = generated_code_review.replace("json", "")
	generated_code_review = generated_code_review.replace("```", "")		

	logger.info(generated_code_review)
	try:
		generated_code_review = json.loads(generated_code_review)			
		updated_code = modify_code(generated_code_review)
		if not preview:
			update_python_file(file_path, updated_code, backup_dir)
	except json.decoder.JSONDecodeError as e:
		print("Error decoding JSON, beause it is not valid.")
		logger.info("Error decoding JSON, beause it is not valid.")
		logger.info(str(e))
		print("ABORTING...!!!")
		logger.info("ABORTING!!!!")
		exit(1)
		
		
def make_openai_request(messages, model = "gpt-4o-mini"):
	
	response = client.chat.completions.create(
		model = model,
		messages = messages)  

	response = response.to_dict()
	message_content = response.get("choices", [{}])[0].get("message", {}).get("content", "No content returned.")
	return message_content


def main():
	parser = argparse.ArgumentParser(description="Path of file which needs to be reviewed")
	parser.add_argument("file")
	parser.add_argument("-b", "--backup-directory", dest="backup_dir", default = "./backup")
	parser.add_argument("--model", default = "gpt-4o-mini")
	parser.add_argument("-p", "--preview", action='store_true')		
	args = parser.parse_args()
	if args.preview:
		logger.info("Preview mode enabled!")
		logger.info(args.preview)
	code_review(args.file, args.model, args.preview, args.backup_dir)


if __name__ == "__main__":
	load_dotenv()
	try:
		API_KEY = os.getenv('OPENAI_API_KEY')
		API_ENDPOINT = os.getenv('OPENAI_ENDPOINT')
		if not API_KEY or not API_ENDPOINT:
			raise ValueError("API key or endpoint is not set in the environment variables.")

		client = AzureOpenAI(
        api_version="",
        azure_endpoint=API_ENDPOINT,
        api_key=API_KEY
		)
	except AuthenticationError:
		print("Invalid OpenAI API key.")
		logger.info("Invalid OpenAI API key.")
		print("ABORTING!!!!")
		logger.info("ABORTING!!!!")
		exit(1)
	except APIConnectionError:
		print("Network error: Could not connect to OpenAI API.")
		logger.info("Network error: Could not connect to OpenAI API.")
		print("ABORTING!!!!")
		logger.info("ABORTING!!!!")
		exit(1)
	except OpenAIError as e:
		logger.info(f"OpenAI API error: {e}")
		logger.info("ABORTING!!!!")
		exit(1)
	except ValueError as e:
		logger.info(e)
		logger.info("ABORTING!!!!")
		exit(1)
	except Exception as e:
		logger.info(f"Unexpected error: {e}")
		logger.info("ABORTING!!!!")
		exit(1)

	main()
