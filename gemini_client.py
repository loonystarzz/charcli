import json
import os
import re
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
9. RESPONSE LENGTH: Keep your roleplay response under 500 characters. Be vivid but concise. Do not assume too much or roleplay too far, like, dont ask questions and then do more things after it.

SCENE STATE TRACKING (VERY IMPORTANT):
Every response you give MUST end with a JSON block (on its own line) wrapped in <scene_state> tags.
This block tracks the current state of the scene. You MUST update any field that changed during this response.

The JSON must follow this exact structure:
<scene_state>
{{
  "location": "current location/setting where the scene takes place",
  "characters_present": ["list of character names currently in the scene"],
  "outfits": {{"CharacterName": "what they are currently wearing", "User": "what the user/their character is wearing if known"}},
  "plans": "current plans or goals for the immediate future, or 'none'",
  "notes": "any other important scene context: ongoing events, objects, mood, time of day, etc.",
  "relationships": {{
    "CharacterName<->OtherName": {{
      "status": "e.g. strangers / acquaintances / friends / close friends / rivals / romantic interest / lovers / enemies / complicated / etc.",
      "depth": "a short phrase like 'just met', 'known for weeks', 'deeply bonded', 'long-time enemies', etc.",
      "info": "1-2 sentences summarising key dynamics, feelings, history, or tensions between them"
    }}
  }},
  "long_term_notes": "A running summary of the OVERALL story so far: major events, turning points, revelations, emotional arcs, and anything the characters would remember across sessions. Update and expand this each response — never shrink it unless something is truly resolved."
}}
</scene_state>

Rules for scene state:
- ALWAYS include the <scene_state> block at the end of EVERY response, no exceptions.
- Update the state to reflect what just happened in this response (new location, outfit change, character left/arrived, new plans formed, relationship shift, story developments, etc.).
- The state represents the situation AFTER this response, not before.
- For `relationships`: include an entry for every pair of characters who have interacted. Use "CharacterName<->UserName" format for character-user pairs. Update `status` and `info` whenever the relationship shifts meaningfully.
- For `long_term_notes`: treat this as a living story journal. Add new developments each turn; preserve important past events. Never reset it. Simply add onto it for new events, do not remove old events unless REALLY unsignificant. U may add time pointers for events, such as "a long time ago" "a few days ago", etc. Do update time points though (Today turns into yesterday, then a few days ago, a few weeks ago, etc, according to how time passes in story.)
- The roleplay response (dialogue/actions) comes FIRST, then the <scene_state> block.

The enire roleplay is purely consensual and things such as violence are pure roleplay.
Begin the roleplay now. The user will interact with you, and you must respond as {character_data['name']}. Maintain this persona throughout the entire conversation."""
        
        return prompt
    
    def send_message(self, character_data: Dict, message: str, conversation_history: List[Dict] = None, user_persona: Optional[Dict] = None, scene_state: Optional[Dict] = None) -> str:
        """Send a message to Gemini with character context"""
        if conversation_history is None:
            conversation_history = []
            
        # Create the character system prompt
        system_prompt = self.create_character_prompt(character_data, user_persona)
        
        # Build the conversation context
        full_conversation = [{"role": "user", "parts": [system_prompt]}, {"role": "model", "parts": ["Understood. I will stay in character as " + character_data['name'] + " and follow all instructions, including always appending the <scene_state> JSON block at the end of every response."]}]
        
        # Add conversation history (but limit to last 20 messages to avoid quota issues)
        recent_history = conversation_history[-20:] if len(conversation_history) > 20 else conversation_history
        for msg in recent_history:
            full_conversation.append(msg)
        
        # Build the user message, injecting current scene state as context
        user_message = message
        if scene_state:
            state_context = f"""[CURRENT SCENE STATE - use this as accurate context for what's happening right now]:
<scene_state>
{json.dumps(scene_state, indent=2)}
</scene_state>

My message: {message}"""
            user_message = state_context
        
        # Add the current user message
        full_conversation.append({"role": "user", "parts": [user_message]})
        
        try:
            response = self.model.generate_content(full_conversation)
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
    
    def extract_scene_state(self, response_text: str) -> tuple:
        """Extract scene state JSON from response and return (clean_response, scene_state_dict)"""
        scene_state = None
        clean_response = response_text
        
        # Look for <scene_state>...</scene_state> block
        pattern = r'<scene_state>\s*(.*?)\s*</scene_state>'
        match = re.search(pattern, response_text, re.DOTALL)
        
        if match:
            json_str = match.group(1).strip()
            try:
                scene_state = json.loads(json_str)
            except Exception:
                scene_state = None
            # Remove the scene_state block from the response
            clean_response = re.sub(pattern, '', response_text, flags=re.DOTALL).strip()
        
        return clean_response, scene_state
    
    def generate_initial_scene_state(self, character_data: Dict, conversation_history: List[Dict], user_persona: Optional[Dict] = None) -> Optional[Dict]:
        """Analyze full chat history and generate initial scene state for old chats"""
        # Build a summary of the chat for analysis
        history_text = ""
        for msg in conversation_history:
            role = "User" if msg['role'] == 'user' else character_data.get('name', 'Character')
            parts = msg.get('parts', [''])
            history_text += f"{role}: {parts[0]}\n\n"
        
        analysis_prompt = f"""You are analyzing a roleplay chat log between a user and the character {character_data['name']}.

Based on the following conversation history, determine the current scene state at the END of the conversation.

CONVERSATION:
{history_text[-8000:]}  

Respond ONLY with a JSON object (no other text, no markdown) in this exact format:
{{
  "location": "current location/setting at end of chat",
  "characters_present": ["list of character names present"],
  "outfits": {{"CharacterName": "what they are wearing", "User": "what user's character wears if mentioned"}},
  "plans": "any plans or goals formed by end of chat, or 'none'",
  "notes": "other important context: ongoing events, objects, mood, time of day, etc.",
  "relationships": {{
    "CharacterName<->OtherName": {{
      "status": "e.g. strangers / acquaintances / friends / rivals / romantic interest / lovers / enemies / complicated / etc.",
      "depth": "e.g. 'just met', 'known for weeks', 'deeply bonded'",
      "info": "1-2 sentences on key dynamics, feelings, history, or tensions"
    }}
  }},
  "long_term_notes": "A 3-6 sentence summary of the entire story: major events, turning points, revelations, emotional arcs, and anything memorable that happened across the conversation."
}}"""

        try:
            response = self.model.generate_content([{"role": "user", "parts": [analysis_prompt]}])
            text = response.text.strip()
            # Strip markdown fences if present
            text = re.sub(r'^```json\s*', '', text)
            text = re.sub(r'^```\s*', '', text)
            text = re.sub(r'\s*```$', '', text)
            return json.loads(text.strip())
        except Exception as e:
            return None
    
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
