import os
import warnings
import wave
import pyaudio
import sys
from tenacity import retry, wait_random_exponential, stop_after_attempt
from openai import AzureOpenAI, AuthenticationError, APIConnectionError, OpenAIError, BadRequestError
from dotenv import load_dotenv
import pyttsx3
import logging
from datetime import datetime
from colorama import Fore, Style
import threading
import time
import sounddevice as sd
import soundfile as sf
import pyfiglet


# Suppress FP16 warning for CPU usage
warnings.filterwarnings(
    "ignore", message="FP16 is not supported on CPU; using FP32 instead")

text = "Welcome to Voice enabled AI Assistant"
ascii_art = pyfiglet.figlet_format(text, width=100)
print(ascii_art)

# Creating directory for logs
if not os.path.exists("logs"):
    os.makedirs("logs")    

if not os.path.exists("recordings"): os.makedirs("recordings")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler("logs/voice_chat.log")
    ]
)

logger = logging.getLogger(__name__)

load_dotenv()


CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1 if sys.platform == "darwin" else 2
RATE = 44100


def record_audio(seconds):

    current_datetime = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    output_path = f"./recordings/user-{current_datetime}.wav"

    # Opening wav file in write binary mode
    with wave.open(output_path, "wb") as wf:
        p = pyaudio.PyAudio()
        info = p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                logging.info(
                    f"Input Device id  {i} - {p.get_device_info_by_host_api_device_index(0, i).get('name')}")

        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)

        stream = p.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, frames_per_buffer=CHUNK, input=True)

        print(Style.BRIGHT + "Speak now...!!!" + Style.RESET_ALL)

        for index in range(0, RATE//CHUNK * seconds):
            if index % (RATE//CHUNK) == 0:
                print(
                    f"\rRecording... {index // (RATE//CHUNK)} / {seconds}s", end="", flush=True)
            wf.writeframes(stream.read(CHUNK))
        print(" Done")

        stream.close()
        p.terminate()
    logging.info(f"File saved: {output_path}")

    return output_path


def openai_client():
    try:
        API_KEY = os.getenv("API_KEY")
        API_ENDPOINT = os.getenv("API_ENDPOINT")

        if not API_KEY:
            raise ValueError

        if not API_ENDPOINT:
            raise ValueError     

        ac = AzureOpenAI(
            api_version="",
            api_key=API_KEY,
            azure_endpoint=API_ENDPOINT
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
    except Exception as e:
        logging.error(
            f"Got following error while creating Azure Client. {str(e)}")
        exit(1)

    return ac


def text_to_speech(text_to_speak):
    # Loading text to speech engine
    try:
        logging.info("Creating speech engine")
        engine = pyttsx3.init()
    except Exception as e:
        logging.error(f"Error initializing pyttsx3 engine: {e}")

    # Get current speed(words per minute) at which speech is being spoken
    rate = engine.getProperty('rate')
    engine.setProperty('rate', rate - 25)


    try:
        logging.info("Speaking text...")
        engine.say(text_to_speak)
        engine.runAndWait()
    except Exception as e:
        logging.error(f"Error during speech generation: {e}")


@retry(wait=wait_random_exponential(min=1, max=20), stop=stop_after_attempt(3))
def openai_chat(ac, messages):
    try:
        response = ac.chat.completions.create(
            model="gpt-5-chat",
            messages=messages
        )

        response = response.to_dict()
        response = response["choices"][0]["message"]["content"]
    except APIConnectionError as e:
        logging.error(f"Error Connecting with AzureOpenAI endpoint : {str(e)}")
        logging.error("ABORTING...!!")
        exit(1)
    except BadRequestError as e:
        logging.error("Malformed Request.")
        logging.error(str(e))
        logging.error("ABORTING...!!")
        exit(1)
    except Exception as e:
        logging.error(str(e))
        logging.error("ABORTING...!!")
        exit(1)

    return response


def slow_print_words(text, delay=0.4):
    #Print each word with a slight delay
    words = text.split()    
    for word in words:
        print(word, end=" ", flush=True)
        time.sleep(delay)
    print()


def voice_chat(ac, model, tts):
    messages = [{"role": "system", "content": "The response will be used convert to speech, so only include english's punctuations and no other special symbols. Keep the responses short and simple."}]
    while True:
        # Recording Audio
        file = record_audio(7)

        # Using whisper to convert audio to text
        result = model.transcribe(file)

        print(Fore.GREEN + "USER: " + Style.BRIGHT +
              f"{result['text']}" + Style.RESET_ALL)
        logging.info(f"role : user , content: {result['text']}")
        # Adding user's message to the chat's history or context
        messages.append({"role": "user", "content": result["text"]})

        # Asking question to LLM
        response = openai_chat(ac, messages)

        # Adding LLM's response to message history or context
        logging.info(f"role : assistant , content: {response}")
        messages.append({"role": "assistant", "content": response})

        #Start both the threads
        # t1 = threading.Thread(target=speak, args=(tts, response, ))        
        # t2 = threading.Thread(target=slow_print_words, args=(
        #     Fore.BLUE + "ASSISTANT: " + Style.BRIGHT + f"{response}" + Style.RESET_ALL,))

        # t1.start()
        # t2.start()

        # t1.join()
        # t2.join()    
        speak_text=response    
        print_text=Fore.BLUE + "ASSISTANT: " + Style.BRIGHT + f"{response}" + Style.RESET_ALL

        speak_and_print(tts,speak_text, print_text)
        logging.info("All threads finished!")

        time.sleep(1)

def speak_and_print(tts, speak_text, print_text):
    # speaker = "Gracie Wise"
    # current_datetime = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    # wav_file_path = f"./recordings/bot-{current_datetime}.wav"
    with torch.inference_mode():
        wav = tts.tts(speak_text)
    sr = tts.synthesizer.output_sample_rate
    try:
        sd.play(wav, sr); 
        slow_print_words(print_text)
        sd.wait()
    except Exception as e:
        logging.exception("Playback failed")    
    finally:
        sd.stop()  

def speak(tts, text):
    # speaker = "Gracie Wise"
    # current_datetime = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    # wav_file_path = f"./recordings/bot-{current_datetime}.wav"
    with torch.inference_mode():
        wav = tts.tts(text)
    sr = tts.synthesizer.output_sample_rate
    try:
        sd.play(wav, sr); 
        sd.wait()
    except Exception as e:
        logging.exception("Playback failed")    
    finally:
        sd.stop()        


if __name__ == "__main__":
    
    # Loading whisper model
    import whisper
    print("Loading Whisper Model....")
    model = whisper.load_model("base")
    print("Whisper Model loaded")

    # Creating Azure OpenAI client
    ac = openai_client()

    device = "cpu"
    
    print("Loading TTS Model....")
    import torch
    from TTS.api import TTS    
    tts = TTS("tts_models/en/ljspeech/tacotron2-DDC",progress_bar=True).to(device)
    print("TTS Model Loaded")
    try:            
        voice_chat(ac, model, tts)
    except KeyboardInterrupt:
        print("Stopping AI Voice Assistant")    
