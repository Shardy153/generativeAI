
# AI-Powered Slack Bot

An intelligent Slack bot that integrates with Large Language Models (LLMs) to provide AI-powered responses and text improvement capabilities.

## Features

- **AI Chat Responses**: Responds to @mentions with AI-generated replies using OpenAI-compatible LLM APIs
- **Text Rewriting**: `/rewrite` slash command for grammar correction and writing improvement
- **Real-time Communication**: Uses Slack Socket Mode for instant message processing
- **Message Logging**: Monitors and logs various Slack events for debugging
- **Multi-channel Support**: Works across public channels, private groups, and direct messages

## Prerequisites

- Python 3.7+
- Slack workspace with admin permissions to create apps
- Access to an OpenAI-compatible LLM API endpoint

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd slack-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` with your actual credentials:
   ```
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_APP_TOKEN=xapp-your-app-token
   LLM_ENDPOINT=https://your-llm-api-endpoint
   LLM_API_KEY=your-llm-api-key
   LLM_MODEL=your-model-name
   ```

## Slack App Configuration

### 1. Create a Slack App

1. Go to [Slack API dashboard](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app and select your workspace

### 2. Required OAuth Scopes

Add these Bot Token Scopes in **OAuth & Permissions**:
- `app_mentions:read` - Read app mentions
- `channels:history` - Read message history in public channels
- `channels:read` - Read public channel information
- `chat:write` - Send messages
- `commands` - Add slash commands
- `groups:history` - Read message history in private channels
- `groups:read` - Read private channel information
- `im:history` - Read direct message history
- `im:read` - Read direct message information
- `mpim:history` - Read group direct message history
- `mpim:read` - Read group direct message information
- `users:read` - Read user information

### 3. Enable Socket Mode

1. Go to **Socket Mode** in your app settings
2. Enable Socket Mode
3. Generate an App-Level Token with `connections:write` scope
4. Copy the token (starts with `xapp-`) to your `.env` file as `SLACK_APP_TOKEN`

### 4. Add Slash Commands

1. Go to **Slash Commands**
2. Create a new command:
   - Command: `/rewrite`
   - Request URL: (not needed for Socket Mode)
   - Short Description: "Improve writing and correct grammar"

### 5. Enable Event Subscriptions

1. Go to **Event Subscriptions**
2. Enable Events
3. Subscribe to these Bot Events:
   - `app_mention` - When the bot is mentioned
   - `message.channels` - Messages in public channels
   - `message.groups` - Messages in private channels
   - `message.im` - Direct messages
   - `message.mpim` - Group direct messages

### 6. Install the App

1. Go to **Install App** in the sidebar
2. Click "Install to Workspace"
3. Copy the Bot User OAuth Token (starts with `xoxb-`) to your `.env` file as `SLACK_BOT_TOKEN`

## Usage

### Running the Bot

```bash
python test.py
```

The bot will start and connect to Slack via Socket Mode. You should see:
```
Starting Slack bot with SocketMode...
Waiting for message events to arrive...
```

### Interacting with the Bot

#### 1. AI Chat Responses
Mention the bot in any channel where it's installed:
```
@YourBot What is the weather like today?
```
The bot will respond with an AI-generated reply.

#### 2. Text Rewriting
Use the `/rewrite` slash command to improve text:
```
/rewrite this text has grammer mistakes and could be better
```
The bot will return a corrected and improved version.

## LLM Configuration

The bot supports any OpenAI-compatible LLM API. Configure these environment variables:

- `LLM_ENDPOINT`: Your LLM API base URL (e.g., `https://api.openai.com/v1` for OpenAI)
- `LLM_API_KEY`: Your API key
- `LLM_MODEL`: Model name to use (e.g., `gpt-3.5-turbo`, `gpt-4`)

### Supported Providers
- OpenAI
- Azure OpenAI
- Local LLM servers (Ollama, vLLM, etc.)
- Any OpenAI-compatible API

## File Structure

```
slack-bot/
├── test.py              # Main bot application
├── llm.py              # LLM integration module
├── requirements.txt    # Python dependencies
├── env.example        # Environment variables template
├── .env              # Your environment variables (create from env.example)
└── README.md         # This file
```

## Code Overview

### Core Components

- **`test.py`**: Main application with event handlers for:
  - App mentions (`@bot` responses)
  - Slash commands (`/rewrite`)
  - Message logging and monitoring
  - Channel and user information utilities

- **`llm.py`**: LLM integration module providing:
  - OpenAI client configuration
  - Chat completion functionality
  - Environment variable validation

### Key Functions

- `mention_handler()`: Processes @mentions and generates AI responses
- `handle_rewrite()`: Handles `/rewrite` slash command
- `get_channel_name()`: Retrieves channel information
- `get_username()`: Retrieves user information
- `llm_client()`: Initializes LLM client
- `chat()`: Sends queries to LLM and returns responses

## Troubleshooting

### Common Issues

1. **Bot not responding to mentions**
   - Ensure the bot is invited to the channel (`/invite @YourBot`)
   - Check that `app_mentions:read` scope is granted
   - Verify Socket Mode is enabled

2. **Slash command not working**
   - Confirm the command is created in Slack app settings
   - Check `commands` scope is granted

3. **LLM errors**
   - Verify `LLM_ENDPOINT`, `LLM_API_KEY`, and `LLM_MODEL` are correct
   - Check API key permissions and rate limits
   - Ensure the model name is available on your LLM provider

4. **Connection issues**
   - Validate both `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN`
   - Ensure tokens have proper scopes
   - Check internet connectivity and firewall settings

### Debug Mode

The bot logs detailed information about events. Check the console output for:
- Connection status messages
- Event details
- Error messages
- LLM request/response information

## License

[Add your license information here]

## Contributing

[Add contributing guidelines here]
