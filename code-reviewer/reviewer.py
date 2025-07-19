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


PROMPT = """You an excellent code reviewer like Github Copilot.
You will recieve a file contents a text. Generate a code review for that file and indiciate what changes should be made to improve its style, efficieny, exception handling, performace, documentation, readability and incorporate best practices. 
If there are any reputable libraries that could be introduced to improve the code, suggest them. Be kind and constructive. I will be replacing the exact old code with new one.
If you add try block for exceptions handling, make sure to add except block as well.
I want all the changes in JSON format. The json should include a line before and a line after code change is suggested in the actual code.
Json format:
{ 	
	"1" : {line_before_code_change: <ONE LINE BEFORE THE CODE>, line_after_code_change: <ONE LINE AFTER THE CODE>, old_code: <OLD_CODE>, new_code: <NEW_CODE>, explanation : , line_number: <line number in the existing code> },
	"2" : {line_before_code_change: <ONE LINE BEFORE THE CODE>, line_after_code_change: <ONE LINE AFTER THE CODE>, old_code: <OLD_CODE>, new_code: <NEW_CODE>, explanation : , line_number: <line number in the existing code> }
}
Note: In old code and new_code fields, use \t for tabs and \n for new line. Please do not add tabs directly, use tabs for them.
Every backslash must be escape, For example, use \\t or \\n instead of \t or \n.
THE RESPONSE SHOULD BE A VALID JSON WHICH CAN BE PARSED IN PYTHON, the values fields should not start with whitespaces
Example:	
Here is code:
<CODE>
import subprocess

output = subprocess.check_output("df -h", shell=True, text=True)
for line in output.splitlines()[1:]:
	line =  line.split()		
	print(line[4])
	line = line[4][:-1]
	print(line)
	print(int(line))
</CODE>
Here is a valid json response changes.	
This is a VALID RESPONSE, because python cannot parse it. There are spaces after ", which makes the json invalid for python.
{
	"1": {
		"line_before_code_change": "",
		"line_after_code_change": "for line in output.splitlines()[1:]:",
		"old_code": "output = subprocess.check_output(\"df -h\", shell=True, text=True)",
		"new_code": "import shlex\n\ncommand = shlex.split(\"df -h\")\noutput = subprocess.check_output(command, text=True)",
		"explanation": "Using shlex to split the command enhances security by avoiding issues related to shell injection attacks due to the shell=True parameter.",
		"line_number": 3
	},
	"2": {
		"line_before_code_change": "line =  line.split()",
		"line_after_code_change": "if len(line) > 4:",
		"old_code": "print(line[4])",
		"new_code": "if len(line) > 4:\n\t\tprint(line[4])",
		"explanation": "Adding a check to ensure there are enough elements in 'line' before accessing index 4 prevents potential IndexError exceptions.",
		"line_number": 5
	},
	"3": {
		"line_before_code_change": "print(line[4])",
		"line_after_code_change": "line = line[4][:-1]",
		"old_code": "line = line[4][:-1]",
		"new_code": "if len(line) > 4:\n\t\tline = line[4][:-1]",
		"explanation": "Adding a check to ensure there are enough elements in 'line' before accessing index 4 prevents potential IndexError exceptions.",
		"line_number": 7
	},
	"4": {
		"line_before_code_change": "print(line)",
		"line_after_code_change": "",
		"old_code": "print(int(line))",
		"new_code": "print(int(line) if line else 0)",
		"explanation": "Adding a conditional check to avoid ValueError if 'line' is empty when converting to int.",
		"line_number": 9
	}
}
Note: Do not add anything else apart from this json
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
