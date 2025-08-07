import os
import json
import weaviate
import logging
import argparse
import pdfplumber
from dotenv import load_dotenv
from tenacity import retry, wait_random_exponential, stop_after_attempt
from openai import AzureOpenAI, AuthenticationError, APIConnectionError, RateLimitError

#Set constants
MODEL_NAME = "text-embedding-3-large"
LOG_FILE = "./logs/pdf_assistant.log"

#Set logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE)        
    ]
)
logger = logging.getLogger(__name__)

#Load env vars from .env file
load_dotenv()

def get_openai_client():
    """ Created OpenAI's client using API Key and API Endpoint provided in the .env file
    Return:
        openai client which can be used to make requests to get embeddings or to ask query
    """
    #Get Key and Endpoint
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_API_ENDPOINT = os.getenv("OPENAI_API_ENDPOINT")
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY does not exists, please check the env file.\nAborting...!!!")
        exit(1)
    if not OPENAI_API_ENDPOINT:
        logger.error("OPENAI_API_ENDPOINT does not exists, please check the env file.\nAborting...!!!")
        exit(1)                
    try:
        #Create OpenAI Client
        openai_client = AzureOpenAI(
            api_version = "",
            azure_endpoint = OPENAI_API_ENDPOINT,
            api_key = OPENAI_API_KEY
        )
        return openai_client
    except APIConnectionError as e:
        logger.error(f"Failed to connect with AzureOpenAI endpoint\nError: {str(e)}\nAborting...!!!")
        exit(1)
    except AuthenticationError as e:
        logger.error(f"Failed to authenticate with AzureOpenAI endpoint\nError: {str(e)}\nAborting...!!!")
        exit(1)
    except Exception as e:
        logger.error(f"Got following exception while creating openai client : {str(e)}")    
        logger.error("Aborting")
        exit(1)


@retry(wait=wait_random_exponential(min=1, max=20),stop=stop_after_attempt(5))
def get_openai_embeddings(openai_client, text):
    try:
        #Generate Embeddings
        response = openai_client.embeddings.create(
            model = MODEL_NAME,
            encoding_format = "float",
            input = text
        )
        #Parse Embedding from the OpenAI's response
        response  = response[0]
        response = response.to_dict()
        return response["embedding"]


    except RateLimitError as e:
        logger.error("You have reached the Rate limit for making openai's requests.")
        logger.error(f"Error: {str(e)}")
    except Exception as e:
        logger.error(f"Got following exception while generating embeddings: {str(e)}")            


def openai_chat(openai_client, context, chat_history):
    """
        Ask Questions to OpenAI.
        Parameters:
            openai_client: Client through which openai is authenticated.
            context: Context generated based on user's query/questions
            chat_history: Chat history between user and assistant
        Return:
            Retrun openai's response in string format.            
    """
    try:
        #Prepare messages for OpenAI Chat
        messages=[
            {"role": "assistant", 
            "content": f"""You will given some text as a context to the questions you will be asked next.
            Note: only use the context to get answers and do not add extra information from your side.
            Context: {context}
            Chat History: {chat_history}?    	
            Assitant:"""},    
        ] 

        #Send message to OpenAI
        response = openai_client.chat.completions.create(
            messages = messages,
            model = "gpt-4o-mini")

        #Parse the content/answer     
        response = response.to_dict()
        response = response["choices"][0]["message"]["content"]	
        return response
    except APIConnectionError as e:
        logger.error(f"Failed to connect with AzureOpenAI endpoint\nError: {str(e)}\nAborting...!!!")
        exit(1)
    except Exception as e:
        logger.error(f"Got following exception while making request to OpenAI : {str(e)}")    
        logger.error("Aborting")
        exit(1)


def store_embeddings(openai_client, pdf_content, collection_name):
    """
    Store embeddings of each page of PDF file in waeviate DB.
    1. Create collection if it does not exists in weaviate DB.
    2. Get all existing contents from Weaviate DB.
    3. Get a list of strings which contains new content i.e. contents for which embeddings is not present.
    4. Get embeddings for each item in new contents list of string.
    5. Store embeddings in Weaviate DB
    Parameters:
        openai_client: The client through which openai requests are made.
        pdf_content([string]): pdf content
        collection_name: Weaviate DB collection name
    """
    #Create weaviate connection client
    client = weaviate.connect_to_local()

    # Create the collection WITHOUT any built-in vectorizer        
    if client.collections.exists(name=collection_name):
        collection_client = client.collections.get(name=collection_name)
    else:
        collection_client = client.collections.create(name=collection_name)    
    
    
    # Get existing content from database to avoid duplicate embeddings
    existing_contents = set()
    try:
        # Query all existing content to check for duplicates
        existing_objects = collection_client.query.fetch_objects(limit=10000)  # Adjust limit as needed
        for obj in existing_objects.objects:
            if obj.properties and "content" in obj.properties:
                existing_contents.add(obj.properties["content"])
        logger.info(f"Found {len(existing_contents)} existing content entries in database")

    except weaviate.exceptions.WeaviateStartUpError as e:
        logger.error(f"Failed to connect with Weaviate DB, {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching existing content: {e}")
        existing_contents = set()

    # Add data with embeddings only for new content
    new_content_count = 0
    with collection_client.batch.dynamic() as batch:
        for content in pdf_content:
            # Skip if content already exists in database
            if content in existing_contents:
                continue
                
            # Generate embeddings only for new content
            vector = get_openai_embeddings(openai_client, content) 
            new_content_count += 1

            batch.add_object(
                properties={
                    "content": content,                    
                },
                vector=vector
            )

            if batch.number_errors > 10:
                print("Batch import stopped due to excessive errors.")
                break
    

    logger.info(f"Added {new_content_count} new content entries with embeddings")
    if new_content_count == 0:
        logger.info("All content already exists in database - no new embeddings generated")

    # Handle errors if any
    failed_objects = collection_client.batch.failed_objects
    if failed_objects:
        logger.error(f"Number of failed imports: {len(failed_objects)}")
        logger.error(f"First failed object: {failed_objects[0]}")

    #Closing the connection
    client.close()    


@retry(wait=wait_random_exponential(min=1, max=20),stop=stop_after_attempt(3))
def get_answer(openai_client, collection_name, query, chat_history):
    """
    Get answer from openai based on user's query.
    1. It first generates the embedding of the user's query.
    2. Get the 5 nearest neighbours of user's query embeddings.
    3. Pass those 5 nearest neighbour's contents to openai as context.
    
    Parameters:
        openai_client: The client through which openai requests are made.
        collection_name: Name of weaviate DB collection name, where the content and embeddings are stored.
        Query(string): User's query
        chat_history: Chat history between user and assistant
    Return:
        answer(string): Response from OpenAI
    """
    try:
    #Connect with weaviate DB
        client = weaviate.connect_to_local()
        collection_client = client.collections.get(name=collection_name)

        # Run a query with manually generated query embedding    
        query_vector = get_openai_embeddings(openai_client, query)

        #Get 5 closest embeddings
        response = collection_client.query.near_vector(query_vector, limit=5)

        #Close client
        client.close()

        #Preparing context for OpenAI
        context = ''    
        for obj in response.objects:
            context = context + " \n" + json.dumps(obj.properties["content"])                    

        #Get answer from OpenAI
        answer = openai_chat(openai_client, context, chat_history)
        logger.info(f"Query: {query}")
        logger.info(f"Answer: {answer}")
        return answer
    except weaviate.exceptions.WeaviateQueryException as e:
        logger.error(f"Failed to query Weaviate DB: {str(e)}") 
    except Exception as e:
        logger.error(f"Got following error while getting nearest vectors")
    
   
def pdf_chat(openai_client, collection_name, pdf_file):
    """
        Start a chat with AI Assistant, You can ask any question related to the PDF.
        Parameters:
            openai_client: Client through which OpenAI requests are made.
            collection_name: Name of weaviate DB collection name, where the content and embeddings are stored.
            pdf_file: Name of the PDF File name
    """
    print(f"Welcome to AI PDF Assistant, it can help you query your pdf file: {pdf_file}.")
    print("Type exit to close the conversation!!!\n")
    chat_history = ''
    # Run the program until user type exit or interrupt the chat
    try:
        while True:
            query = input("User: ")    
            if query.strip().lower() == "exit":
                break
            chat_history += f"User: {query}"
            logger.info(f"User: {query}")
            answer = get_answer(openai_client, collection_name, query, chat_history)
            chat_history += f"Assistant: {query}"
            print(f"Assistant: {answer}")
            print("\n")
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected. Exiting gracefully...")    
        exit(0)
    

def read_pdf(pdf_file):  
    """
    Reads the content of PDF file page by page.
    Parameters:
        pdf_file(string): The path of pdf file
    Returns:
        pdf_content : The list of strings which contains pdf file's contents
    """  
    pdf_text_content = []
    try :
        #Parse PDF Content page by page
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:            
                page_content = page.extract_text()  
                if page_content:                 
                    pdf_text_content.append(page_content)                
        return pdf_text_content          
    except FileNotFoundError as fe:
        logger.error(f"{pdf_file} does not exists. {str(fe)} \nAborting!!!")
        exit(1)
    except PermissionError as e:
        logger.error(f"Not have enough permission to read {pdf_file}.\nError: {str(e)} \nAborting...!!!")
        exit(1)
    except Exception as e:
        logger.error(f"Error while reading PDF file, {str(e)}\nAborting...!!!")
        exit(1)          


def parse_arguments():
    #Parse arguments like PDF file name and Query
    parser = argparse.ArgumentParser(
            prog='PDF File AI Assistant',
            description="User can ask questions with respect to the pdf file provided as argument.",
            epilog='Text at the bottom of help')
    parser.add_argument("-p", "--pdf-file",  help="PDF file for which we need to create embeddings")    
    args = parser.parse_args()
    if not args.pdf_file:
        logger.error("pdf file cannot be empty, you must provide pdf file name. Aborting!!!")
        exit(1)    
    isExist = os.path.exists(args.pdf_file) 
    if not isExist:
        logger.error("PDF file does not exists, please make sure the path is correct or file exists. Aborting...!!!")
        exit(1)
    
    return args.pdf_file


if __name__ == "__main__":    

    #Parse Arguments
    pdf_file = parse_arguments()

    #Get content of PDF file in list of strings
    pdf_text_content = read_pdf(pdf_file)    

    #Get OpenAI Client
    openai_client = get_openai_client()

    #Generate collection name
    collection_name = pdf_file.split("/")[-1].replace(".pdf", "").lower()
    logging.info(f"Collection Name is : {collection_name}")
    
    #Generate and Store embeddings in Weaviate DB
    store_embeddings(openai_client, pdf_text_content, collection_name)        
    
    #Start chat with AI Assistant
    pdf_chat(openai_client, collection_name, pdf_file)

 
