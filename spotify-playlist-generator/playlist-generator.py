import os
import json
import spotipy
import logging
import argparse
import pprint
from openai import AzureOpenAI, OpenAIError, AuthenticationError, APIConnectionError, APITimeoutError, BadRequestError
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

if not os.path.exists("logs"):
    os.makedirs("logs")
    print("Directory logs created.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler("logs/playlist_generator.log")        
    ]
)

logger = logging.getLogger(__name__)

def get_song_list_spotify(playlist_name, generated_playlist_dict):
    oauth_object = spotipy.SpotifyOAuth(scope='playlist-modify-private')
    token_dict = oauth_object.get_access_token()
    token = token_dict['access_token']
    spotifyObject = spotipy.Spotify(auth=token)
    user_name = spotifyObject.current_user()
    user_id = user_name["id"]
    songs = []
    for track in generated_playlist_dict:    
        logger.info(f"Searching for track: {track['song']}")
        results = spotifyObject.search(q=f'track: {track["song"]}, artist: {track["artist"]}', limit=5, type="track" )
        songs_dict = results['tracks']        
        song_name = songs_dict['items'][0]['name']        
        song_items = songs_dict['items']
        song = song_items[0]['external_urls']['spotify']
        songs.append(song)
        logger.info(f"Fetched song: {song_name}")
    
    playlist = spotifyObject.user_playlist_create(user_id, playlist_name, public=False, collaborative=False, description="This playlist is generated through Generative AI.")            
    spotifyObject.user_playlist_add_tracks(user_id, playlist["id"], songs)
    print(f"Playlist name: {playlist_name}, link: {playlist['external_urls']['spotify']}")


def openai_chat(openai_client, messages, model="gpt-4o-mini"):
    try:
        response = openai_client.chat.completions.create(
        model = model,
        messages = messages)  

        response = response.to_dict()
        message_content = response.get("choices", [{}])[0].get("message", {}).get("content", "No content returned.")
        return message_content 

    except APIConnectionError as e:
        print(f"Error Connecting with AzureOpenAI endpoint : {str(e)}")
        print("ABORTING...!!")
        exit(1)
    except APITimeoutError as e:
        print(f"Request Timed out: {str(e)}")        
        print("ABORTING...!!")
        exit(1)
    except BadRequestError as e:
        print("Malformed Request.")
        print(str(e))            
        print("ABORTING...!!")
        exit(1)
    except Exception as e:
        print(str(e))            
        print("ABORTING...!!")
        exit(1)

def openai_auth(API_KEY, API_ENDPOINT):
    try:        
        openai_client = AzureOpenAI(
        api_version="",
        azure_endpoint=API_ENDPOINT,
        api_key=API_KEY
        )
        return openai_client
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
    except Exception as e:
        logger.info(f"Unexpected error: {e}")
        logger.info("ABORTING!!!!")
        exit(1)


if __name__ == "__main__":    
    try:

        parser = argparse.ArgumentParser(
                    prog='Spotify Playlist Generator',
                    description="Based on the description provided by the user, playlist will generated on user's account.",
                    epilog='Text at the bottom of help')

        parser.add_argument('-d', '--description', help="Describe you mood/event for which you want to generate playlist")           # positional argument
        parser.add_argument('-n', '--number', default = 10, help="Number of songs that needs to be added to the playlist")      # option that takes a value
        parser.add_argument('-l', '--language', default="hindi", help="Language of songs, it can be hindi/english.")
        args = parser.parse_args()
        logger.info(f"description of the playlist : {args.description}")                    
        logger.info(f"Number of songs that need to be added to the playlist : {args.number}")
        logger.info(f"Language : {args.language}")

        if not args.description:
            logger.error("Description cannot be empty, please provide some description.")
            logger.error("ABORTING")
            exit(1)

        API_KEY = os.getenv('OPENAI_API_KEY')
        API_ENDPOINT = os.getenv('OPENAI_ENDPOINT')
        if not API_KEY or not API_ENDPOINT:
            raise ValueError("API key or endpoint is not set in the environment variables.")

        openai_client = openai_auth(API_KEY, API_ENDPOINT)        
        if openai_client:
            prompt = """
            You are spotify playlist generator. I will provide you with a mood or situation or event or even a artist/album name. You will have to generate a playlist for me. The playlist should be in a python-valid JSON.
            In the prompt, user will provide description of the playlist, or it can include an event or a artist name as well.
            Thr prompt will also include the number of songs that needs to be added, and the language of the songs. The language can be hindi or english.
            If the language picked is hindi, then pick songs in Hindi language i.e. songs from bollywood i.e. songs created in India.
            for each track, include, name of the artist and name of the song. Also generate a nice name for the playlist.           
            Exmaple format:
            ```json
            {
                "PLAYLIST_NAME" : "NAME OF THE PLAYLIST",
                "1" :
                {
                    artist : <ARTIST_NAME>
                    song : <SONG NAME>
                },
                "2": 
                {
                    artist : <ARTIST_NAME>
                    song :   <SONG NAME>
                }, 
                "3": {
                    artist : <ARTIST_NAME>
                    song :   <SONG NAME>
                }
            }```        
            """
            user_prompt = f"Generate a playlist with following description: {args.description}, it should have {args.number} songs and the language of songs should be {args.language}."
            messages = [{"role": "system", "content" : prompt }, {"role": "user", "content": user_prompt}]
            generated_playlist = openai_chat(openai_client, messages)
            generated_playlist = generated_playlist.replace("```json", "").replace("```","")
            generated_playlist_dict = json.loads(generated_playlist)    
            playlist_name = generated_playlist_dict["PLAYLIST_NAME"]            
            del generated_playlist_dict["PLAYLIST_NAME"]                        
            logger.info(f"Playlist JSON: {generated_playlist_dict.values()}")
            get_song_list_spotify(playlist_name, generated_playlist_dict.values())        


    except ValueError as e:
        logger.info(e)
        logger.info("ABORTING!!!!")
        exit(1)
    except json.decoder.JSONDecodeError as e:
        print("Error decoding JSON, beause it is not valid.")
        logger.info("Error decoding JSON, beause it is not valid.")
        logger.info(str(e))
        print("ABORTING...!!!")
        logger.info("ABORTING!!!!")
        exit(1)    
    except Exception as e:
        logger.info(f"Unexpected error: {e}")
        logger.info("ABORTING!!!!")
        exit(1)
