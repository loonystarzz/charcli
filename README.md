# charcli - Gemini TUI Roleplay Client

A terminal-based chat client for Google's Gemini AI that allows you to roleplay with multiple AI characters. Each character has their own personality, background, and speech patterns.

## Features

- **Multiple Characters**: Create and manage different AI characters with unique personalities
- **Character Profiles**: JSON-based character files with detailed information (name, age, personality, speech patterns, etc.)
- **User Personas**: Switch between different user personas to make characters respond to you differently
- **Multiple Chats**: Open multiple chat sessions with different characters or the same character
- **Immersive Scenarios**: Each character has custom opening scenarios for immediate roleplay immersion
- **Persistent Characters**: Characters are saved as JSON files in the `characters/` directory

## Installation

1. Clone or download this project
2. Set up your Gemini API key:
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API key
# Get your free API key from: https://makersuite.google.com/app/apikey
```

3. Install:
```bash
./install.sh
```

4. Run the application:
```bash
run charcli in terminal (may need to logout and login again / reopen terminal!!)
```

## Usage

### Rich TUI Interface 
1. **Select a Character**: Choose from available characters in the character selection screen
2. **Select Persona (Optional)**: Choose a user persona to influence how characters respond to you
3. **Start Chatting**: Type your messages and press Enter to chat with the character
4. **Multiple Chats**: Start a new chat with any character
5. **Quit**: Press Ctrl+C to exit


## Character Format

Characters are defined as JSON files in the `characters/` directory. Each character file contains:

```json
{
  "name": "Character Name",
  "age": 25,
  "title": "Character Title",
  "basic_info": "Brief description of the character",
  "personality": "Detailed personality traits",
  "speech_patterns": [
    "Example phrase 1",
    "Example phrase 2"
  ],
  "appearance": "Physical description",
  "background": "Character backstory",
  "goals": "Character's motivations",
  "fears": "Character's fears",
  "scenario": "The opening scenario that sets the scene for the roleplay. This will be the first message you see when starting a chat with this character."
}
```

## Included Characters

The project comes with three sample characters:

1. **Lyra** - Warrior Maiden of the Northern Realms
2. **Eldrin** - Master of the Arcane Archives  
3. **Raven** - Shadow of the Underworld

## Creating New Characters

To create a new character:

1. Create a new JSON file in the `characters/` directory
2. Follow the character format shown above
3. The character will automatically appear in the character selection screen

## User Personas

Personas allow you to define how characters should perceive and respond to you. Create personas in the `personas/` directory:

```json
{
  "name": "Persona Name",
  "info": "Description of who you are as this persona. Characters will respond to you based on this information."
}
```

### Included Personas

The project comes with three sample personas:

1. **Adventurer** - Brave explorer seeking treasure and excitement
2. **Scholar** - Learned academic who values knowledge above all else  
3. **Merchant** - Shrewd businessperson focused on trade and profit

### Creating New Personas

1. Create a new JSON file in the `personas/` directory
2. Use the persona format shown above
3. The persona will automatically appear in the persona selection screen

## Requirements

- Python 3.7+
- Google Gemini API key (free)
- Internet connection for API calls

