import json
import os
import google.generativeai as genai
from typing import Dict, List, Optional

class GeminiClient:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')
        
    def create_character_prompt(self, character_data: Dict, user_persona: Optional[Dict] = None) -> str:
        """Create a system prompt based on character data"""
        persona_info = ""
        if user_persona:
            persona_info = f"""

USER PERSONA INFORMATION:
The person you are interacting with is: {user_persona['name']}
About them: {user_persona['info']}
You should respond to them as if they are this type of person. Adapt your responses accordingly while staying in character."""
        
        prompt = f"""You are roleplaying as {character_data['name']}, {character_data['title']}. 

Character Details:
- Name: {character_data['name']}
- Age: {character_data['age']}
- Title: {character_data['title']}
- Basic Info: {character_data['basic_info']}
- Personality: {character_data['personality']}
- Appearance: {character_data['appearance']}
- Background: {character_data['background']}
- Goals: {character_data['goals']}
- Fears: {character_data['fears']}

Speech Patterns and Examples:
{chr(10).join(f"- {pattern}" for pattern in character_data['speech_patterns'])}
{persona_info}

IMPORTANT ROLEPLAYING INSTRUCTIONS:
1. Stay in character at all times as {character_data['name']}
2. Use the speech patterns and personality traits described above
3. Respond naturally to the user's messages while maintaining character consistency
4. Draw from your background, goals, and fears to inform your responses
5. Never break character or mention that you are an AI
6. Keep responses engaging and in character
7. Use the speech examples as inspiration for your natural dialogue style
8. CRITICAL FORMATTING RULE: Use quotation marks ("") for all spoken dialogue and asterisks (**) for all actions, movements, and descriptions. Example: "You seem quite... mysterious." *He stares at you across the table, trying to read you* "You know, I think I've taken a liking to you."

Begin the roleplay now. The user will interact with you, and you must respond as {character_data['name']}. Maintain this persona throughout the entire conversation."""
        
        return prompt
    
    def send_message(self, character_data: Dict, message: str, conversation_history: List[Dict] = None, user_persona: Optional[Dict] = None) -> str:
        """Send a message to Gemini with character context"""
        if conversation_history is None:
            conversation_history = []
            
        # Create the character system prompt
        system_prompt = self.create_character_prompt(character_data, user_persona)
        
        # Build the conversation context
        full_conversation = [{"role": "user", "parts": [system_prompt]}, {"role": "model", "parts": ["Understood. I will stay in character as " + character_data['name'] + " and follow all instructions."]}]
        
        # Add conversation history (but limit to last 20 messages to avoid quota issues)
        recent_history = conversation_history[-20:] if len(conversation_history) > 20 else conversation_history
        for msg in recent_history:
            full_conversation.append(msg)
        
        # Add the current user message
        full_conversation.append({"role": "user", "parts": [message]})
        
        try:
            response = self.model.generate_content(full_conversation)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
    
    def create_chat_session(self, character_data: Dict, user_persona: Optional[Dict] = None) -> str:
        """Create a new chat session with character"""
        system_prompt = self.create_character_prompt(character_data, user_persona)
        try:
            chat = self.model.start_chat(history=[{"role": "user", "parts": [system_prompt]}])
            return chat
        except Exception as e:
            print(f"Error creating chat session: {e}")
            return None

class PersonaManager:
    def __init__(self, personas_dir: str):
        self.personas_dir = personas_dir
        self.personas = {}
        self.current_persona = None
        self.load_personas()
    
    def load_personas(self):
        """Load all persona JSON files"""
        if not os.path.exists(self.personas_dir):
            os.makedirs(self.personas_dir)
            return
            
        for filename in os.listdir(self.personas_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.personas_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        persona_data = json.load(f)
                        self.personas[filename[:-5]] = persona_data  # Remove .json extension
                except Exception as e:
                    print(f"Error loading persona {filename}: {e}")
    
    def get_persona(self, persona_name: str) -> Optional[Dict]:
        """Get persona data by name"""
        return self.personas.get(persona_name)
    
    def get_all_personas(self) -> Dict[str, Dict]:
        """Get all available personas"""
        return self.personas
    
    def set_current_persona(self, persona_name: str):
        """Set the current active persona"""
        if persona_name is None:
            self.current_persona = None
            return True
        persona = self.get_persona(persona_name)
        if persona:
            self.current_persona = persona
            return True
        return False
    
    def get_current_persona(self) -> Optional[Dict]:
        """Get the current active persona"""
        return self.current_persona
    
    def save_persona(self, persona_name: str, persona_data: Dict):
        """Save persona data to file"""
        filepath = os.path.join(self.personas_dir, f"{persona_name}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(persona_data, f, indent=2, ensure_ascii=False)
            self.personas[persona_name] = persona_data
        except Exception as e:
            print(f"Error saving persona {persona_name}: {e}")

class CharacterManager:
    def __init__(self, characters_dir: str):
        self.characters_dir = characters_dir
        self.characters = {}
        self.load_characters()
    
    def load_characters(self):
        """Load all character JSON files"""
        if not os.path.exists(self.characters_dir):
            os.makedirs(self.characters_dir)
            return
            
        for filename in os.listdir(self.characters_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.characters_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        character_data = json.load(f)
                        self.characters[filename[:-5]] = character_data  # Remove .json extension
                except Exception as e:
                    print(f"Error loading character {filename}: {e}")
    
    def get_character(self, character_name: str) -> Optional[Dict]:
        """Get character data by name"""
        return self.characters.get(character_name)
    
    def get_all_characters(self) -> Dict[str, Dict]:
        """Get all available characters"""
        return self.characters
    
    def save_character(self, character_name: str, character_data: Dict):
        """Save character data to file"""
        filepath = os.path.join(self.characters_dir, f"{character_name}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(character_data, f, indent=2, ensure_ascii=False)
            self.characters[character_name] = character_data
        except Exception as e:
            print(f"Error saving character {character_name}: {e}")
