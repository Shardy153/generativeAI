import os
from slack_bolt import App, logger
from dotenv import load_dotenv
from slack_bolt.adapter.socket_mode import SocketModeHandler
import json
import sys
import llm
import pprint

# Load environment variables
load_dotenv()

# Get tokens from environment
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

# Validate required environment variables
if not SLACK_BOT_TOKEN:
    print("Error: SLACK_BOT_TOKEN environment variable is not set")
    sys.exit(1)

if not SLACK_APP_TOKEN:
    print("Error: SLACK_APP_TOKEN environment variable is not set")
    sys.exit(1)

print("Using SLACK_BOT_TOKEN (first 10 chars):", SLACK_BOT_TOKEN[:10] + "...")
print("Using SLACK_APP_TOKEN (first 10 chars):", SLACK_APP_TOKEN[:10] + "...")

# Initialize the app with timeout settings
app = App(
    token=SLACK_BOT_TOKEN    
)


def get_channel_name(channel_id):
    """
    Get channel name from channel ID using conversations.info
    """
    try:
        result = app.client.conversations_info(channel=channel_id)        
        if result["ok"]:
            channel_info = result["channel"]
            return channel_info["name"]
        else:
            logger.error(f"Error getting channel info: {result['error']}")
            return None
    except Exception as e:
        logger.error(f"Exception getting channel info: {e}")
        return None


def get_username(user_id):
    """
    Get username from user ID using users.info
    """
    try:
        result = app.client.users_info(user=user_id)        
        if result["ok"]:
            user_info = result["user"]
            # Return display name if available, otherwise username
            return user_info.get("profile", {}).get("display_name") or user_info.get("name")
        else:
            logger.error(f"Error getting user info: {result['error']}")
            return None
    except Exception as e:
        logger.error(f"Exception getting user info: {e}")
        return None


def get_user_info(user_id):
    """
    Get full user information from user ID
    Returns a dictionary with all user details
    """
    try:
        result = app.client.users_info(user=user_id)
        if result["ok"]:
            return result["user"]
        else:
            logger.error(f"Error getting user info: {result['error']}")
            return None
    except Exception as e:
        logger.error(f"Exception getting user info: {e}")
        return None


# Event handlers for various Slack events
@app.event("dnd_updated_user")
def handle_dnd_updated_user_events(body, logger):
    logger.info(f"DND Update Event: {body}")


@app.event("member_joined_channel")
def handle_member_joined_channel_events(body, logger):
    logger.info(f"Member Joined Channel Event: {body}")

@app.command("/rewrite")
def handle_rewrite(ack, respond, command):
    ack()  
    print(command)  
    text = command.get("text")
    # event = body.get("event")
    # print(event)
    llm_client = llm.llm_client()
    print(f"User query: {text}")
    query = f"Improve writing and correct grammar in the following text and do not add anything else in the response: {text}"
    response = llm.chat(llm_client, query)
    # thread_id = event.get("thread_ts") or event.get("ts")
    # if thread_id:
        # print(f"Bot mentioned in thread {thread_id}, replying in thread")
    respond(response)    
    


@app.event("app_mention")
def mention_handler(body, say):
    """Handle a bot mention event by responding with a message."""
    event = body.get("event", {})    
    user_id = event.get("user")
    text = event.get("text")
    ts = event.get("ts")
    if '>' in text:
        text = text.split('>', 1)[1].strip()

    print(event)
    channel_id = event.get("channel")
    thread_id = event.get("thread_ts") or event.get("ts")
    
    # Get LLM response
    llm_client = llm.llm_client()
    print(f"User query: {text}")
    response = llm.chat(llm_client, text)
    pprint.pp(response)
    
    # Reply in thread if the mention was in a thread, otherwise reply normally
    if thread_id:
        print(f"Bot mentioned in thread {thread_id}, replying in thread")
        say(response, thread_ts=thread_id)
    else:
        print("Bot mentioned in channel, replying normally")
        say(response)

@app.event("message")
def handle_message_events(body, logger):
    """Handle all message events regardless of channel type"""
    event = body.get("event", {})
    
    # Skip bot messages to avoid infinite loops
    if event.get("subtype") == "bot_message":
        return
    
    channel_id = event.get("channel")
    user_id = event.get("user")
    text = event.get("text", "")
    
    # print("=" * 50)
    # print("NEW MESSAGE EVENT RECEIVED")
    # print("=" * 50)
    # print(f"Event type: {body.get('event_type')}")
    # print(f"Channel ID: {channel_id}")
    # print(f"User ID: {user_id}")
    # print(f"Text: {text}")
    
    # Try to get channel name
    if channel_id:
        channel_name = get_channel_name(channel_id)
        # print(f"Channel Name: {channel_name}")
    
    # Try to get username
    if user_id:
        username = get_username(user_id)
        # print(f"Username: {username}")
    
    # print("=" * 50)
    
    # Log the full event for debugging purposes
    logger.debug(f"Full message event: {json.dumps(event, indent=2)}")


# Define a separate message handler for messages (this ensures we capture all message types)
@app.message()
def log_message(message, say):
    """Handle direct message events"""
    # Skip bot messages to avoid infinite loops
    if message.get("subtype") == "bot_message":
        return
    
    channel_id = message["channel"]
    user_id = message.get("user")
    text = message.get("text", "")
    
    print("=" * 50)
    print("DIRECT MESSAGE HANDLED")
    print("=" * 50)
    print(f"Channel ID: {channel_id}")
    print(f"User ID: {user_id}")
    print(f"Text: {text}")
    
    # Try to get channel name
    if channel_id:
        channel_name = get_channel_name(channel_id)
        print(f"Channel Name: {channel_name}")
    
    # Try to get username
    if user_id:
        username = get_username(user_id)
        print(f"Username: {username}")
    
    print("=" * 50)

if __name__ == "__main__":
    # Print startup message
    print("Starting Slack bot with SocketMode...")
    print("Waiting for message events to arrive...")
    
    # Create an app-level token with connections:write scope
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    
    print("SocketMode handler created. Starting socket mode...")
    
    try:
        handler.start()
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
    except Exception as e:
        print(f"\nError starting bot: {e}")
        sys.exit(1)
