import os
import pickle
import logging
import argparse
import tiktoken 
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from tenacity import retry, wait_random_exponential, stop_after_attempt
from openai import AzureOpenAI, OpenAIError, AuthenticationError, APIConnectionError, APITimeoutError, RateLimitError


MODEL_NAME = "text-embedding-3-large"
MODEL_COST_PER_MILLION = 0.13
EMBEDDING_CACHE_PATH = "movies_embeddings_cache.pkl"
DATASET_PATH = "./wiki_movie_plots_deduped.csv"

load_dotenv()

if not os.path.exists("logs"):
    os.makedirs("logs")
    print("Directory logs created.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler("logs/embeddings.log")        
    ]
)

logger = logging.getLogger(__name__)

try:
	embedding_cache = pd.read_pickle(EMBEDDING_CACHE_PATH)
	if not isinstance(embedding_cache, dict):
		logging.error("embedding_cache is not a valid dictionary.")	
		logging.error("Aborting...!!")
		exit(1)
except FileNotFoundError:
	embedding_cache = {}

def get_cost(movie_plots):
	"""
	Calculates the number of tokens will be consumed to make the request to openai
	Also prints the cost of the requests in dollars 
	"""
	enc = tiktoken.encoding_for_model(MODEL_NAME)
	total_tokens = sum([len(enc.encode(plot)) for plot in movie_plots ])
	logging.info(f"Total Number of Tokens: {total_tokens}")	
	cost = (total_tokens/1000000) * MODEL_COST_PER_MILLION
	logging.info(f"Total cost of Querying OpenAI : {cost}$")

def get_openai_client(API_ENDPOINT,API_KEY):
	try:	
		openai_client = AzureOpenAI(
			api_version = "",
			azure_endpoint = API_ENDPOINT,
			api_key = API_KEY)	
		return 	openai_client
	except AuthenticationError as e:
		logging.error(f"Error authenticating to Azure Endpoint: {str(e)}")
		exit(1)
	except APITimeoutError as e:
		logging.error(f"Request made to OpenAI timedout: {str(e)}")		
		exit(1)
	except APIConnectionError as e:
		logging.error(f"Error connecting with the Azure Endpoint: {str(e)}")		
		exit(1)
	except OpenAIError as e	:
		logging.error(f"OpenAI Error: {str(e)}")
		exit(1)
	except Exception as e:	
		logging.error(str(e))
		exit(1)

@retry(wait=wait_random_exponential(min=1, max=20),stop=stop_after_attempt(5))
def get_embedding(openai_client, text):
	"""
	Get embeddings of a string from openai
	Parametes:
		openai_client: The client through openai api calls are being made.
		text (string): The string for which embeddings will be generated.

	Returns:
		Return embedding of the string passed.	
	"""

	text = text.replace("\n", " ")
	try:
		response = openai_client.embeddings.create(
			input= text,
			model =  MODEL_NAME, 
			encoding_format = "float")
		response  = response[0]
		response = response.to_dict()
		return response["embedding"]
	except RateLimitError as e:
		logging.info("You have reached rate limits, please slow down.")
		logging.info(f"Here is the error: {str(e)}")
	except APIConnectionError as e:
		logging.error(f"Error connecting with the Azure Endpoint: {str(e)}")		
	except OpenAIError as e	:
		logging.error(f"OpenAI Error: {str(e)}")
	except Exception as e:	
		logging.error(str(e))		

def get_embedding_string(openai_client, text, embedding_cache = embedding_cache):
	"""
	Get the embeddings of the text passed, if the embeddings of the text is not present in a pkl file, then openai api will be called to get the embeddings and stored in the pkl file
	Parameters:
		openai_client: The client though which openai clients are being made.
	Returns:
		Return the embedding either from GenAi or from the cache stored in the file.	
	"""
	
	model = MODEL_NAME
	if (text, model) not in embedding_cache.keys():
		logging.info("Getting Embedding from OpenAI...")
		embedding_cache[(text, model)] = get_embedding(openai_client, text, model)
		if embedding_cache[(text, model)]:
			with open(EMBEDDING_CACHE_PATH, "wb") as embedding_cache_file:
				pickle.dump(embedding_cache, embedding_cache_file)
		else:
			logger.warning("Could not get embedding for a movie plot, skipping this one.")
	return embedding_cache[(text, model)]		


def get_movie_recommendations(movie, movies_titles, plot_embeddings, k):
	"""
	Generates a list of recommended movies based on the input movie
	Parameter:
		movie(string) : The name of the movie that needs to be searched
		movies_list (list) : The list of movies where the movie will be searched
		plot_embeddings (Numpy Array): It contains embeddings of plots of all the movies in movies_list
		n (int): Number of recommendations
	Returns:
		movie_recommendations_list (list): List of recommended movies.	
	"""

	index = np.where(movies_titles == movie)
	if len(index) == 0:
		logging.error("Movie does not exists in the movie list.Please check the CSV file and try gaian with a valid movie name.")
		logging.error("Aborting")
		exit(1)
	query_movie_plot = plot_embeddings[index[0][0]]	
	norm_query = query_movie_plot / np.linalg.norm(query_movie_plot)
	norm_all = plot_embeddings / np.linalg.norm(plot_embeddings, axis=1, keepdims=True)
	similarities = np.dot(norm_all, norm_query)    
	top_k_indices = np.argsort(similarities)[::-1][:k+1]	
	logging.info(f"Indices of closest/similar strings : {top_k_indices}")
	movie_recommendations_list = []
	for index in top_k_indices:
		if movies_titles[index] == movie:
			continue
		movie_recommendations_list.append(movies_titles[index])
	return movie_recommendations_list


def main():
	try:
		parser = argparse.ArgumentParser(
                    prog='Movie recommendations generator',
                    description="Provide movie and get recommendations.",
                    epilog='Text at the bottom of help')

		parser.add_argument('-m', '--movie', help="Name the movie that you want recommendations for.")           # positional argument
		parser.add_argument('-n', '--number', type=int, default = 10, help="Number of movie recommendations")      # option that takes a value        
		args = parser.parse_args()
		logger.info(f"description of the playlist : {args.movie}")                    
		logger.info(f"Number of songs that need to be added to the playlist : {args.number}")        

		if not args.movie:
			logger.error("Movie name should not be empty")
			logger.error("ABORTING")
			exit(1)

		if args.number not in range(1,15):
			logger.error("Number of recommendations should be between 1 and 15.")     
			logger.error("ABORTING")
			exit(1)

	except ValueError as e:
		logger.error(e)
		logging.error("ABORTING")
		exit(1)

	API_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
	API_KEY = os.getenv("OPENAI_API_KEY")

	if not API_ENDPOINT or not API_KEY:
		raise ValueError("API KEY or API ENDPOINT is not set in the environment variables.")

	openai_client = get_openai_client(API_ENDPOINT, API_KEY)	
	
	try:
		movies_df = pd.read_csv(DATASET_PATH)
		logging.info("CSV loaded successfully.")
		movies_data = movies_df[movies_df["Origin/Ethnicity"] == "Bollywood"].sort_values("Release Year", ascending=False).head(2500)	
		movie_plots = movies_data["Plot"].values		
	except FileNotFoundError as e:
		logging.error(f"{DATASET_PATH} does not exists.")		
	except pd.errors.EmptyDataError as e:
		logging.error(f"{DATASET_PATH} is empty")
	except pd.errors.ParseError as p:
		print(f"Error parsing the CSV file '{DATASET_PATH}': {e}")	
	except Exception as e:
		print(f"An unexpected error occurred: {e}")			
	
	get_cost(movie_plots)
	plot_embeddings = []
	for plot in movie_plots:
		embedding = get_embedding_string(openai_client, plot)
		if embedding is not None:
			plot_embeddings.append(embedding)
		else:
			logger.warning("Null embedding encountered, skipping plot.")	
	movies_titles = movies_data["Title"].values
	
	movie_recommendations_list = get_movie_recommendations(args.movie, movies_titles, plot_embeddings, args.number)	
	if len(movie_recommendations_list) > 0:
		print("\nHere are your movie recommendations:")
		for idx, movie in enumerate(movie_recommendations_list, 1):
			print(f"{idx}. {movie}")
	else:
		print("No recommendations found for the given movie.")


if __name__ == "__main__":
	main()
	
