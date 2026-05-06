#!/usr/bin/env python3
import curses
import json
import os
import textwrap
from datetime import datetime
from typing import Dict, List, Optional
from gemini_client import GeminiClient, CharacterManager, PersonaManager

class MenuCursesInterface:
    def __init__(self, gemini_client, character_manager, persona_manager):
        self.gemini_client = gemini_client
        self.character_manager = character_manager
        self.persona_manager = persona_manager
        self.current_character = None
        self.conversation_history = []
        self.chat_lines = []
        self.input_buffer = ""
        self._cursor_pos = 0
        self._dot_command = False  # True after pressing '.' waiting for second key
        self.running = True
        
        # Menu state
        self.current_screen = "main"  # "main", "chat"
        self.main_menu_focus = 0
        self.character_focus = 0
        self.persona_focus = 0
        self.selected_character = None
        self.selected_persona = None
        
        # Chat persistence
        self.chats_dir = os.path.join(os.path.dirname(__file__), "chats")
        self.current_chat_id = None
        self.saved_chats = {}
        self.last_auto_save = 0
        self.last_api_call = 0  # For rate limiting
        self.scroll_offset = 0  # Scroll offset for chat history
        self.load_saved_chats()
        
    def run(self):
        """Main run loop"""
        try:
            # Initialize curses
            stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            stdscr.keypad(True)
            
            # Try to make cursor visible, handle terminal compatibility
            try:
                curses.curs_set(1)  # Normal cursor
            except:
                try:
                    curses.curs_set(2)  # Very visible cursor
                except:
                    pass  # Cursor visibility not supported in this terminal
            
            # Colors
            if curses.has_colors():
                curses.start_color()
                curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)   # Title
                curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Selected
                curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Instructions
                curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Character name
                curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Focus
                curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Default text
                curses.init_pair(7, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Action text (**)
                curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_BLACK)   # Light gray for quotes ("") - using black with dim
            
            # Main loop
            while self.running:
                if self.current_screen == "main":
                    self.show_main_menu(stdscr)
                elif self.current_screen == "chat":
                    self.chat_loop(stdscr)
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            curses.endwin()
    
    def show_main_menu(self, stdscr):
        """Show main selection menu"""
        h, w = stdscr.getmaxyx()
        
        while self.current_screen == "main" and self.running:
            stdscr.clear()
            
            # Title
            title = "=== charcli ==="
            stdscr.addstr(0, (w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
            
            # Main menu options
            menu_items = ["Select Character (for new chat)", "Select Persona (all chats)", "Start New Chat", "Load old Chat", "Character Maker", "Persona Maker", "Quit"]
            menu_y = 3
            
            for i, item in enumerate(menu_items):
                attr = curses.color_pair(5) | curses.A_BOLD if i == self.main_menu_focus else curses.A_NORMAL
                prefix = "→ " if i == self.main_menu_focus else "  "
                stdscr.addstr(menu_y + i, 4, f"{prefix}{item}", attr)
            
            # Current selections info
            info_y = menu_y + len(menu_items) + 2
            if self.selected_character is not None:
                characters = list(self.character_manager.get_all_characters().items())
                if self.selected_character < len(characters):
                    char_name = characters[self.selected_character][1]['name']
                    stdscr.addstr(info_y, 4, f"Character: {char_name}", curses.color_pair(2))
            
            if self.selected_persona is not None:
                personas = list(self.persona_manager.get_all_personas().items())
                if self.selected_persona == 0:
                    persona_name = "No Persona"
                elif self.selected_persona - 1 < len(personas):
                    persona_name = personas[self.selected_persona - 1][1]['name']
                else:
                    persona_name = "Unknown"
                stdscr.addstr(info_y + 1, 4, f"Persona: {persona_name}", curses.color_pair(2))
            
            # Instructions
            inst_y = info_y + 3
            instructions = [
                "↑↓ - Navigate menu",
                "Enter - Select option",
                "q - Quit"
            ]
            for i, inst in enumerate(instructions):
                stdscr.addstr(inst_y + i, 4, inst, curses.color_pair(3))
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            if key == ord('q'):
                self.running = False
                break
            elif key == curses.KEY_UP:
                if self.main_menu_focus > 0:
                    self.main_menu_focus -= 1
            elif key == curses.KEY_DOWN:
                if self.main_menu_focus < len(menu_items) - 1:
                    self.main_menu_focus += 1
            elif key == ord('\n'):  # Enter
                if self.main_menu_focus == 0:  # Select Character
                    self.show_character_selection(stdscr)
                elif self.main_menu_focus == 1:  # Select Persona
                    self.show_persona_selection(stdscr)
                elif self.main_menu_focus == 2:  # Start Chat
                    if self.selected_character is not None:
                        self.apply_selections()
                        self.start_chat_session()
                        self.current_screen = "chat"
                    else:
                        # Show error
                        stdscr.addstr(inst_y + 3, 4, "Please select a character first!", curses.color_pair(3) | curses.A_BOLD)
                        stdscr.refresh()
                        stdscr.getch()
                elif self.main_menu_focus == 3:  # Load Chat
                    self.show_load_chat_menu(stdscr)
                elif self.main_menu_focus == 4:  # Character Editor
                    self.show_character_editor(stdscr)
                elif self.main_menu_focus == 5:  # Persona Editor
                    self.show_persona_editor(stdscr)
                elif self.main_menu_focus == 6:  # Quit
                    self.running = False
    
    def show_character_selection(self, stdscr):
        """Show character selection screen"""
        h, w = stdscr.getmaxyx()
        characters = list(self.character_manager.get_all_characters().items())
        
        while self.running:
            stdscr.clear()
            
            # Title
            title = "SELECT CHARACTER"
            stdscr.addstr(0, (w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
            
            # Character list
            list_y = 3
            for i, (name, data) in enumerate(characters):
                attr = curses.color_pair(5) | curses.A_BOLD if i == self.character_focus else curses.A_NORMAL
                marker = "→ " if i == self.character_focus else "  "
                selected = " ✓" if self.selected_character == i else ""
                stdscr.addstr(list_y + i, 4, f"{marker}{i}. {data['name']} - {data['title']}{selected}", attr)
            
            # Instructions
            inst_y = list_y + len(characters) + 2
            instructions = [
                "↑↓ - Navigate",
                "Enter - Select character",
                "Esc - Back to main menu"
            ]
            for i, inst in enumerate(instructions):
                stdscr.addstr(inst_y + i, 4, inst, curses.color_pair(3))
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            if key == 27:  # Esc
                break
            elif key == curses.KEY_UP:
                if self.character_focus > 0:
                    self.character_focus -= 1
            elif key == curses.KEY_DOWN:
                if self.character_focus < len(characters) - 1:
                    self.character_focus += 1
            elif key == ord('\n'):  # Enter
                self.selected_character = self.character_focus
                break
    
    def show_persona_selection(self, stdscr):
        """Show persona selection screen"""
        h, w = stdscr.getmaxyx()
        personas = list(self.persona_manager.get_all_personas().items())
        
        while self.running:
            stdscr.clear()
            
            # Title
            title = "SELECT PERSONA"
            stdscr.addstr(0, (w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
            
            # Persona list (including "No Persona")
            list_y = 3
            persona_items = [("No Persona", 0)] + [(data['name'], i+1) for i, (name, data) in enumerate(personas)]
            
            for i, (display_name, value) in enumerate(persona_items):
                attr = curses.color_pair(5) | curses.A_BOLD if i == self.persona_focus else curses.A_NORMAL
                marker = "→ " if i == self.persona_focus else "  "
                selected = " ✓" if self.selected_persona == value else ""
                stdscr.addstr(list_y + i, 4, f"{marker}{value}. {display_name}{selected}", attr)
            
            # Instructions
            inst_y = list_y + len(persona_items) + 2
            instructions = [
                "↑↓ - Navigate",
                "Enter - Select persona",
                "Esc - Back to main menu"
            ]
            for i, inst in enumerate(instructions):
                stdscr.addstr(inst_y + i, 4, inst, curses.color_pair(3))
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            if key == 27:  # Esc
                break
            elif key == curses.KEY_UP:
                if self.persona_focus > 0:
                    self.persona_focus -= 1
            elif key == curses.KEY_DOWN:
                if self.persona_focus < len(persona_items) - 1:
                    self.persona_focus += 1
            elif key == ord('\n'):  # Enter
                self.selected_persona = persona_items[self.persona_focus][1]
                break
    
    def apply_selections(self):
        """Apply the current selections"""
        # Apply character selection
        if self.selected_character is not None:
            characters = list(self.character_manager.get_all_characters().items())
            if self.selected_character < len(characters):
                char_name, char_data = characters[self.selected_character]
                self.current_character = char_data
        
        # Apply persona selection
        if self.selected_persona == 0:
            self.persona_manager.set_current_persona(None)
        elif self.selected_persona is not None and self.selected_persona > 0:
            personas = list(self.persona_manager.get_all_personas().items())
            if self.selected_persona - 1 < len(personas):
                persona_name, persona_data = personas[self.selected_persona - 1]
                self.persona_manager.set_current_persona(persona_name)
    
    def chat_loop(self, stdscr):
        """Main chat loop"""
        h, w = stdscr.getmaxyx()
        
        # Only initialize if this is a new chat (no existing data)
        if not self.chat_lines:
            current_persona = self.persona_manager.get_current_persona()
            self.conversation_history = []
            self.chat_lines = []
            scenario = self.current_character.get('scenario', f"Hello! I'm {self.current_character['name']}. {self.current_character['basic_info']}")
            self.add_message(self.current_character['name'], scenario)
            self.save_current_chat()
        
        # Build display lines once (rebuild when chat changes)
        display_lines = []
        self._rebuild_display = True
        
        while self.current_screen == "chat" and self.running:
            # Auto-save check
            current_time = datetime.now().timestamp()
            if self.last_auto_save == 0 or current_time - self.last_auto_save > 30:
                self.save_current_chat()
                self.last_auto_save = current_time
            
            # Rebuild display lines if needed
            if self._rebuild_display:
                display_lines = self._build_display_lines(w)
                self._rebuild_display = False
            
            # Calculate input box size
            input_lines = self._get_input_lines(w - 4)
            input_height = max(1, len(input_lines))
            min_input_height = 1
            max_input_height = min(5, h // 3)
            input_height = max(min_input_height, min(input_height, max_input_height))
            
            # Layout: title(1) + chat(remaining) + separator(1) + input(input_height) + status(1)
            chat_height = h - 2 - input_height - 1  # title + separator + status
            
            stdscr.clear()
            
            # Title bar
            title = f" Chat with {self.current_character['name']} "
            stdscr.addstr(0, 0, title.center(w), curses.color_pair(1) | curses.A_BOLD)
            
            # Chat area with scrolling
            total_lines = len(display_lines)
            max_scroll = max(0, total_lines - chat_height)
            
            # Clamp scroll offset
            if self.scroll_offset > max_scroll:
                self.scroll_offset = max_scroll
            
            # Determine which lines to show
            if self.scroll_offset == 0:
                # Default: show bottom (newest)
                start = max(0, total_lines - chat_height)
            else:
                # Scrolled up from bottom
                start = max(0, total_lines - chat_height - self.scroll_offset)
            
            # Render chat lines
            for i in range(chat_height):
                line_idx = start + i
                if line_idx < total_lines:
                    line = display_lines[line_idx]
                    if line.startswith('['):
                        stdscr.addstr(i + 1, 0, line[:w-1], curses.color_pair(4) | curses.A_BOLD)
                    else:
                        self.display_formatted_line(stdscr, i + 1, 2, line, w - 2)
            
            # Scroll indicator on right side of chat area
            if total_lines > chat_height:
                # Show position indicator
                if self.scroll_offset > 0:
                    pct = int((start / max_scroll) * 100) if max_scroll > 0 else 0
                    indicator = f"↑{pct}%"
                else:
                    indicator = "↓end"
                stdscr.addstr(chat_height, w - len(indicator) - 1, indicator, curses.color_pair(3))
            
            # Separator line
            sep_y = chat_height + 1
            for i in range(w):
                stdscr.addch(sep_y, i, curses.ACS_HLINE, curses.color_pair(6))
            
            # Calculate cursor position first
            cursor_line, cursor_col = self._get_input_cursor_pos(w - 4)
            cursor_line = min(cursor_line, input_height - 1)
            
            # Input box with border
            input_y = sep_y + 1
            # Draw input lines with visual cursor indicator
            for i in range(input_height):
                if i < len(input_lines):
                    if i == 0:
                        stdscr.addstr(input_y + i, 0, ">> ", curses.A_BOLD)
                        # Add visual cursor indicator on this line if it's the cursor line
                        if i == cursor_line and cursor_col < len(input_lines[i]):
                            # Draw text before cursor
                            stdscr.addstr(input_y + i, 3, input_lines[i][:cursor_col])
                            # Highlight cursor position with reverse video
                            if cursor_col < len(input_lines[i]):
                                stdscr.addch(input_y + i, 3 + cursor_col, input_lines[i][cursor_col], curses.A_REVERSE)
                            # Draw text after cursor
                            if cursor_col + 1 < len(input_lines[i]):
                                stdscr.addstr(input_y + i, 3 + cursor_col + 1, input_lines[i][cursor_col + 1:])
                        else:
                            stdscr.addstr(input_y + i, 3, input_lines[i])
                    else:
                        # Add visual cursor indicator on this line if it's the cursor line
                        if i == cursor_line and cursor_col < len(input_lines[i]):
                            # Draw text before cursor
                            stdscr.addstr(input_y + i, 3, input_lines[i][:cursor_col])
                            # Highlight cursor position with reverse video
                            if cursor_col < len(input_lines[i]):
                                stdscr.addch(input_y + i, 3 + cursor_col, input_lines[i][cursor_col], curses.A_REVERSE)
                            # Draw text after cursor
                            if cursor_col + 1 < len(input_lines[i]):
                                stdscr.addstr(input_y + i, 3 + cursor_col + 1, input_lines[i][cursor_col + 1:])
                        else:
                            stdscr.addstr(input_y + i, 3, input_lines[i])
                else:
                    if i == 0:
                        stdscr.addstr(input_y + i, 0, ">> ", curses.A_BOLD)
            
            # Position cursor in input box
            try:
                if cursor_line == 0:
                    stdscr.move(input_y + cursor_line, 3 + cursor_col)
                else:
                    stdscr.move(input_y + cursor_line, 3 + cursor_col)
            except:
                pass
            
            # Status line
            status_y = h - 1
            if self.scroll_offset > 0:
                status = f"↑ Scrolled up | ↑↓=scroll PgUp/Dn=page | .r=redo | Esc=menu"
            else:
                status = "↑↓=scroll PgUp/Dn=page | ←→=cursor | .+r=redo | Esc=menu | Enter=send"
            stdscr.addstr(status_y, 0, status[:w-1], curses.color_pair(3))
            
            stdscr.refresh()
            
            # Get input with timeout for auto-save
            stdscr.timeout(1000)
            key = stdscr.getch()
            if key == -1:
                continue
            
            # Handle key
            self._handle_chat_key(stdscr, key, chat_height, max_scroll)
    
    def _build_display_lines(self, width):
        """Build wrapped display lines from chat_lines"""
        display_lines = []
        current_sender = None
        for line in self.chat_lines:
            if line.startswith('['):
                end_bracket = line.find(']')
                if end_bracket != -1:
                    sender = line[1:end_bracket]
                    content = line[end_bracket + 2:]
                    if sender != current_sender:
                        display_lines.append(f"[{sender}]:")
                        current_sender = sender
                    if content.strip():
                        display_lines.extend(self.wrap_text(content, width - 4))
            else:
                display_lines.extend(self.wrap_text(line, width - 4))
        return display_lines
    
    def _get_input_lines(self, max_width):
        """Get the input buffer split into display lines"""
        if not self.input_buffer:
            return [""]
        return self.wrap_text(self.input_buffer, max_width)
    
    def _get_input_cursor_pos(self, max_width):
        """Get cursor line and column position in the input box"""
        text_before_cursor = self.input_buffer[:self._cursor_pos]
        lines = self.wrap_text(text_before_cursor, max_width)
        if not lines:
            return 0, 0
        cursor_line = len(lines) - 1
        cursor_col = len(lines[-1])
        return cursor_line, cursor_col
    
    def _handle_chat_key(self, stdscr, key, chat_height, max_scroll):
        """Handle key input in chat mode"""
        # Esc - back to main menu
        if key == 27:
            self.save_current_chat()
            self.current_screen = "main"
            self.scroll_offset = 0
            return
        
        # Up arrow - scroll chat up (see older messages)
        if key == curses.KEY_UP:
            self.scroll_offset = min(self.scroll_offset + 3, max_scroll)
            return
        
        # Down arrow - scroll chat down (see newer messages)
        if key == curses.KEY_DOWN:
            self.scroll_offset = max(0, self.scroll_offset - 3)
            return
        
        # Page Up - scroll chat up a full page
        if key == curses.KEY_PPAGE:
            self.scroll_offset = min(self.scroll_offset + chat_height, max_scroll)
            return
        
        # Page Down - scroll chat down a full page
        if key == curses.KEY_NPAGE:
            self.scroll_offset = max(0, self.scroll_offset - chat_height)
            return
        
        # Dot command: .+r = regenerate (must be held together)
        if key == ord('.') and not self.input_buffer:
            # Check if r is immediately following
            stdscr.timeout(100)  # Short timeout to detect held keys
            next_key = stdscr.getch()
            if next_key == ord('r'):
                self.regenerate_last(stdscr)
                return
            elif next_key != -1:
                # r not pressed, treat . as normal input
                self.input_buffer += '.'
                self._cursor_pos += 1
            return
        # Enter - send message
        if key == ord('\n'):
            if self.input_buffer.strip():
                self.scroll_offset = 0
                self._rebuild_display = True
                self.send_message(stdscr)
                self.input_buffer = ""
                self._cursor_pos = 0
            return
        
        # Backspace - handle multiple possible key codes
        if key == curses.KEY_BACKSPACE or key == 127 or key == 8 or key == 263:  # Various backspace codes
            if self._cursor_pos > 0:
                self.input_buffer = self.input_buffer[:self._cursor_pos-1] + self.input_buffer[self._cursor_pos:]
                self._cursor_pos -= 1
            return
        
        # Delete
        if key == curses.KEY_DC:
            if self._cursor_pos < len(self.input_buffer):
                self.input_buffer = self.input_buffer[:self._cursor_pos] + self.input_buffer[self._cursor_pos+1:]
            return
        
        # Left arrow - move cursor left in input
        if key == curses.KEY_LEFT:
            if self._cursor_pos > 0:
                self._cursor_pos -= 1
            return
        
        # Right arrow - move cursor right in input
        if key == curses.KEY_RIGHT:
            if self._cursor_pos < len(self.input_buffer):
                self._cursor_pos += 1
            return
        
        # Home - cursor to start
        if key == curses.KEY_HOME:
            self._cursor_pos = 0
            return
        
        # End - cursor to end
        if key == curses.KEY_END:
            self._cursor_pos = len(self.input_buffer)
            return
        
        # Printable characters
        if 32 <= key <= 126:
            char = chr(key)
            self.input_buffer = self.input_buffer[:self._cursor_pos] + char + self.input_buffer[self._cursor_pos:]
            self._cursor_pos += 1
    
    def display_formatted_line(self, stdscr, y, x, text, max_width):
        """Display text with color formatting for quotes and actions"""
        current_x = x
        i = 0
        text_len = len(text)
        in_quotes = False
        in_action = False
        
        while i < text_len and current_x < x + max_width:
            # Check for quote start
            if not in_quotes and not in_action and i + 1 < text_len and text[i] == '"' and text[i+1] == '"':
                in_quotes = True
                stdscr.addch(y, current_x, '"', curses.color_pair(8) | curses.A_DIM)
                current_x += 1
                stdscr.addch(y, current_x, '"', curses.color_pair(8) | curses.A_DIM)
                current_x += 1
                i += 2
                continue
            
            # Check for quote end
            if in_quotes and i + 1 < text_len and text[i] == '"' and text[i+1] == '"':
                in_quotes = False
                stdscr.addch(y, current_x, '"', curses.color_pair(8) | curses.A_DIM)
                current_x += 1
                stdscr.addch(y, current_x, '"', curses.color_pair(8) | curses.A_DIM)
                current_x += 1
                i += 2
                continue
            
            # Check for action start
            if not in_action and not in_quotes and i + 1 < text_len and text[i] == '*' and text[i+1] == '*':
                in_action = True
                stdscr.addch(y, current_x, '*', curses.color_pair(7))
                current_x += 1
                stdscr.addch(y, current_x, '*', curses.color_pair(7))
                current_x += 1
                i += 2
                continue
            
            # Check for action end
            if in_action and i + 1 < text_len and text[i] == '*' and text[i+1] == '*':
                in_action = False
                stdscr.addch(y, current_x, '*', curses.color_pair(7))
                current_x += 1
                stdscr.addch(y, current_x, '*', curses.color_pair(7))
                current_x += 1
                i += 2
                continue
            
            # Regular character
            if in_quotes:
                stdscr.addch(y, current_x, text[i], curses.color_pair(8) | curses.A_DIM)
            elif in_action:
                stdscr.addch(y, current_x, text[i], curses.color_pair(7))
            else:
                stdscr.addch(y, current_x, text[i], curses.color_pair(6))
            
            current_x += 1
            i += 1
    
    def wrap_text(self, text, width):
        """Wrap text to fit within width"""
        if len(text) <= width:
            return [text]
        
        lines = []
        current_line = ""
        
        for word in text.split(' '):
            if len(current_line) + len(word) + 1 <= width:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    lines.append(current_line)
                # Handle words longer than width
                if len(word) > width:
                    # Break up long words
                    for i in range(0, len(word), width):
                        lines.append(word[i:i+width])
                else:
                    current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def add_message(self, sender, message):
        """Add message to chat with proper format"""
        # Split message by newlines to handle pre-formatted AI responses
        message_parts = message.split('\n')
        for part in message_parts:
            if part.strip():  # Only add non-empty parts
                self.chat_lines.append(f"[{sender}]: {part}")
        
        # Update conversation history
        self.conversation_history.append({"role": "user" if sender == "You" else "model", "parts": [message]})
        
        # Keep chat history manageable
        if len(self.chat_lines) > 100:
            self.chat_lines = self.chat_lines[-50:]
    
    def _show_waiting_indicator(self, stdscr):
        """Show 'AI is answering...' indicator on screen before blocking API call"""
        try:
            h, w = stdscr.getmaxyx()
            msg = f" {self.current_character['name']} is thinking... "
            stdscr.addstr(h - 3, (w - len(msg)) // 2, msg, curses.color_pair(3) | curses.A_BOLD)
            stdscr.refresh()
        except:
            pass
    
    def send_message(self, stdscr=None):
        """Send message to AI"""
        # Check rate limiting (wait 2 seconds between API calls)
        current_time = datetime.now().timestamp()
        if current_time - self.last_api_call < 2:
            # Show rate limit message
            self.chat_lines.append("[System]: Please wait 2 seconds between messages...")
            return
        
        # Add user message
        self.add_message("You", self.input_buffer)
        
        # Show "AI is answering..." indicator
        self._show_waiting_indicator(stdscr)
        
        # Get AI response
        current_persona = self.persona_manager.get_current_persona()
        try:
            response = self.gemini_client.send_message(
                self.current_character, 
                self.input_buffer, 
                self.conversation_history[:-1],  # Exclude the message we just added
                current_persona
            )
            self.last_api_call = current_time
            
            # Add AI response
            self.add_message(self.current_character['name'], response)
            
            # Auto-save chat
            self.save_current_chat()
        except Exception as e:
            # Handle API errors
            error_msg = f"[System]: API Error: {str(e)}"
            self.chat_lines.append(error_msg)
            self.last_api_call = current_time
    
    def regenerate_last(self, stdscr):
        """Regenerate the last AI response"""
        # Find the last AI message in conversation_history
        if not self.conversation_history:
            self.chat_lines.append("[System]: Nothing to regenerate.")
            return
        
        # Find last model message index in conversation_history
        last_model_idx = -1
        for i in range(len(self.conversation_history) - 1, -1, -1):
            if self.conversation_history[i]['role'] == 'model':
                last_model_idx = i
                break
        
        if last_model_idx == -1:
            self.chat_lines.append("[System]: No AI response to regenerate.")
            return
        
        # Find the user message that preceded it
        last_user_idx = -1
        for i in range(last_model_idx - 1, -1, -1):
            if self.conversation_history[i]['role'] == 'user':
                last_user_idx = i
                break
        
        if last_user_idx == -1:
            self.chat_lines.append("[System]: No user message found to regenerate from.")
            return
        
        # Get the user message text
        user_msg = self.conversation_history[last_user_idx]['parts'][0]
        
        # Remove the last AI response from conversation_history
        self.conversation_history = self.conversation_history[:last_model_idx]
        
        # Remove the last AI response from chat_lines
        char_name = self.current_character['name']
        # Remove from the end: find and remove the last block of AI lines
        while self.chat_lines and self.chat_lines[-1].startswith(f"[{char_name}]:"):
            self.chat_lines.pop()
        # Also remove any system messages at the end
        while self.chat_lines and self.chat_lines[-1].startswith("[System]:"):
            self.chat_lines.pop()
        
        # Show "AI is answering..." indicator
        self._show_waiting_indicator(stdscr)
        
        # Re-send the user message
        current_persona = self.persona_manager.get_current_persona()
        try:
            response = self.gemini_client.send_message(
                self.current_character,
                user_msg,
                self.conversation_history,
                current_persona
            )
            self.last_api_call = datetime.now().timestamp()
            
            # Add the new AI response
            self.add_message(char_name, response)
            self._rebuild_display = True  # Force rebuild since we changed the display
            self.save_current_chat()
        except Exception as e:
            self.chat_lines.append(f"[System]: API Error: {str(e)}")
            self.last_api_call = datetime.now().timestamp()
    
    def load_saved_chats(self):
        """Load all saved chats from the chats directory"""
        if not os.path.exists(self.chats_dir):
            os.makedirs(self.chats_dir)
            return
        
        for filename in os.listdir(self.chats_dir):
            if filename.endswith('.json'):
                chat_id = filename[:-5]  # Remove .json extension
                filepath = os.path.join(self.chats_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        chat_data = json.load(f)
                        self.saved_chats[chat_id] = chat_data
                except Exception as e:
                    print(f"Error loading chat {filename}: {e}")
    
    def save_current_chat(self):
        """Save the current chat to disk"""
        if not self.current_chat_id or not self.current_character:
            return
        
        chat_data = {
            'id': self.current_chat_id,
            'character_name': self.current_character['name'],
            'character_data': self.current_character,
            'persona': self.persona_manager.get_current_persona(),
            'conversation_history': self.conversation_history,
            'chat_lines': self.chat_lines,
            'last_updated': str(datetime.now())
        }
        
        filepath = os.path.join(self.chats_dir, f"{self.current_chat_id}.json")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(chat_data, f, indent=2, ensure_ascii=False)
            self.saved_chats[self.current_chat_id] = chat_data
        except Exception as e:
            print(f"Error saving chat {self.current_chat_id}: {e}")
    
    def start_new_chat(self):
        """Start a new chat session"""
        # Generate unique chat ID
        char_name = self.current_character['name'].lower().replace(' ', '_')
        timestamp = str(int(datetime.now().timestamp()))
        self.current_chat_id = f"{char_name}_{timestamp}"
        
        # Reset chat data
        self.conversation_history = []
        self.chat_lines = []
        
        # Add scenario message
        scenario = self.current_character.get('scenario', f"Hello! I'm {self.current_character['name']}. {self.current_character['basic_info']}")
        self.add_message(self.current_character['name'], scenario)
    
    def start_chat_session(self):
        """Start chat session (always start new when selected from main menu)"""
        # Always start a new chat when selected from main menu
        self.start_new_chat()
    
    def show_load_chat_menu(self, stdscr):
        """Show menu to load existing chats"""
        h, w = stdscr.getmaxyx()
        chat_list = list(self.saved_chats.items())
        chat_focus = 0
        
        while self.running:
            stdscr.clear()
            
            # Title
            title = "LOAD CHAT"
            stdscr.addstr(0, (w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
            
            # Chat list
            list_y = 3
            if not chat_list:
                stdscr.addstr(list_y, 4, "No saved chats found.", curses.color_pair(3))
            else:
                for i, (chat_id, chat_data) in enumerate(chat_list):
                    attr = curses.color_pair(5) | curses.A_BOLD if i == chat_focus else curses.A_NORMAL
                    marker = "→ " if i == chat_focus else "  "
                    char_name = chat_data['character_name']
                    last_updated = chat_data.get('last_updated', 'Unknown')
                    stdscr.addstr(list_y + i, 4, f"{marker}{char_name} - {last_updated[:19]}", attr)
            
            # Instructions
            inst_y = list_y + max(len(chat_list), 1) + 2
            instructions = [
                "↑↓ - Navigate",
                "Enter - Load chat",
                "Esc - Back to main menu"
            ]
            for i, inst in enumerate(instructions):
                stdscr.addstr(inst_y + i, 4, inst, curses.color_pair(3))
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            if key == 27:  # Esc
                break
            elif key == curses.KEY_UP:
                if chat_focus > 0:
                    chat_focus -= 1
            elif key == curses.KEY_DOWN:
                if chat_focus < len(chat_list) - 1:
                    chat_focus += 1
            elif key == ord('\n'):  # Enter
                if chat_list:
                    chat_id, chat_data = chat_list[chat_focus]
                    self.load_chat(chat_data)
                    self.current_screen = "chat"
                    break
    
    def load_chat(self, chat_data):
        """Load a saved chat"""
        self.current_chat_id = chat_data['id']
        self.current_character = chat_data['character_data']
        
        # Restore conversation history properly
        self.conversation_history = chat_data.get('conversation_history', [])
        
        # Restore chat lines properly
        self.chat_lines = chat_data.get('chat_lines', [])
        
        # Set persona if it exists
        persona_data = chat_data.get('persona')
        if persona_data:
            # Find the persona by name and set it
            personas = self.persona_manager.get_all_personas()
            for name, data in personas.items():
                if data['name'] == persona_data['name']:
                    self.persona_manager.set_current_persona(name)
                    break
        else:
            self.persona_manager.set_current_persona(None)
        
        # Update selected character and persona to match loaded chat
        characters = list(self.character_manager.get_all_characters().items())
        for i, (name, data) in enumerate(characters):
            if data['name'] == self.current_character['name']:
                self.selected_character = i
                break
        
        personas = list(self.persona_manager.get_all_personas().items())
        if persona_data:
            for i, (name, data) in enumerate(personas):
                if data['name'] == persona_data['name']:
                    self.selected_persona = i + 1  # +1 because 0 is "No Persona"
                    break
    
    def show_character_editor(self, stdscr):
        """Show character editor interface"""
        h, w = stdscr.getmaxyx()
        
        # Character fields definition
        fields = {
            'name': {'label': 'Name:', 'value': '', 'required': True},
            'age': {'label': 'Age:', 'value': '', 'required': True},
            'title': {'label': 'Title:', 'value': '', 'required': True},
            'basic_info': {'label': 'Basic Info:', 'value': '', 'required': True},
            'personality': {'label': 'Personality:', 'value': '', 'required': True},
            'speech_patterns': {'label': 'Speech Patterns (comma-separated):', 'value': '', 'required': False},
            'appearance': {'label': 'Appearance:', 'value': '', 'required': True},
            'background': {'label': 'Background:', 'value': '', 'required': True},
            'goals': {'label': 'Goals:', 'value': '', 'required': True},
            'fears': {'label': 'Fears:', 'value': '', 'required': True},
            'scenario': {'label': 'Scenario:', 'value': '', 'required': True},
            'filename': {'label': 'Filename (no spaces):', 'value': '', 'required': True}
        }
        
        field_names = list(fields.keys())
        current_field = 0
        editing = True
        
        while editing and self.running:
            stdscr.clear()
            
            # Title
            title = "CHARACTER EDITOR"
            stdscr.addstr(0, (w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
            
            # Instructions
            instructions = "↑↓: Navigate | Enter: Edit field | Tab: Next field | \\: Save | Esc: Cancel"
            stdscr.addstr(1, 2, instructions, curses.color_pair(3))
            
            # Display fields
            y_pos = 3
            for i, field_name in enumerate(field_names):
                field = fields[field_name]
                label = field['label']
                value = field['value']
                
                # Show field label
                label_attr = curses.color_pair(5) | curses.A_BOLD if i == current_field else curses.A_NORMAL
                stdscr.addstr(y_pos, 2, label, label_attr)
                
                # Wrap field value for display
                max_value_width = w - len(label) - 5
                if value:
                    wrapped_lines = self.wrap_text(value, max_value_width)
                    for j, line in enumerate(wrapped_lines):
                        if y_pos + j < h - 3:  # Don't go beyond screen
                            value_attr = curses.color_pair(2) if value else curses.color_pair(8)
                            stdscr.addstr(y_pos + j, len(label) + 3, line, value_attr)
                    y_pos += len(wrapped_lines) - 1  # Account for wrapped lines
                else:
                    stdscr.addstr(y_pos, len(label) + 3, "", curses.color_pair(8))
                
                y_pos += 1
            
            # Status line
            if current_field < len(field_names):
                current_field_name = field_names[current_field]
                status = f"Editing: {fields[current_field_name]['label']} | "
                if fields[current_field_name]['required']:
                    status += "Required field"
                else:
                    status += "Optional field"
            else:
                status = "Ready to save"
            
            stdscr.addstr(h-2, 2, status, curses.color_pair(3))
            
            # Save/Cancel hints
            stdscr.addstr(h-1, 2, "\: Save Character | Esc: Cancel", curses.color_pair(3))
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            if key == 27:  # Esc - cancel
                editing = False
            elif key == curses.KEY_UP:
                if current_field > 0:
                    current_field -= 1
            elif key == curses.KEY_DOWN:
                if current_field < len(field_names) - 1:
                    current_field += 1
            elif key == ord('\t'):  # Tab - next field
                if current_field < len(field_names) - 1:
                    current_field += 1
            elif key == ord('\\'):  # \ - save
                # Validate required fields
                valid = True
                error_msg = ""
                
                for field_name in field_names:
                    field = fields[field_name]
                    if field['required'] and not field['value'].strip():
                        valid = False
                        error_msg = f"Required field '{field['label']}' is empty"
                        break
                
                # Validate filename
                if valid and 'filename' in fields:
                    filename = fields['filename']['value'].strip()
                    if not filename:
                        valid = False
                        error_msg = "Filename is required"
                    elif ' ' in filename:
                        valid = False
                        error_msg = "Filename cannot contain spaces"
                
                if valid:
                    self.save_character(fields)
                    stdscr.addstr(h-2, 2, "Character saved successfully!", curses.color_pair(2))
                    stdscr.refresh()
                    stdscr.getch()
                    editing = False
                else:
                    stdscr.addstr(h-2, 2, f"Error: {error_msg}", curses.color_pair(3) | curses.A_BOLD)
                    stdscr.refresh()
                    stdscr.getch()
            elif key == ord('\n'):  # Enter - edit field
                if current_field < len(field_names):
                    field_name = field_names[current_field]
                    new_value = self.edit_field_value(stdscr, fields[field_name]['label'], fields[field_name]['value'])
                    if new_value is not None:
                        fields[field_name]['value'] = new_value
    
    def show_persona_editor(self, stdscr):
        """Show persona editor interface"""
        h, w = stdscr.getmaxyx()
        
        # Persona fields definition
        fields = {
            'name': {'label': 'Name:', 'value': '', 'required': True},
            'info': {'label': 'Info:', 'value': '', 'required': True},
            'filename': {'label': 'Filename (no spaces):', 'value': '', 'required': True}
        }
        
        field_names = list(fields.keys())
        current_field = 0
        editing = True
        
        while editing and self.running:
            stdscr.clear()
            
            # Title
            title = "PERSONA EDITOR"
            stdscr.addstr(0, (w - len(title)) // 2, title, curses.color_pair(1) | curses.A_BOLD)
            
            # Instructions
            instructions = "↑↓: Navigate | Enter: Edit field | Tab: Next field | \\: Save | Esc: Cancel"
            stdscr.addstr(1, 2, instructions, curses.color_pair(3))
            
            # Display fields
            y_pos = 3
            for i, field_name in enumerate(field_names):
                field = fields[field_name]
                label = field['label']
                value = field['value']
                
                # Show field label
                label_attr = curses.color_pair(5) | curses.A_BOLD if i == current_field else curses.A_NORMAL
                stdscr.addstr(y_pos, 2, label, label_attr)
                
                # Wrap field value for display
                max_value_width = w - len(label) - 5
                if value:
                    wrapped_lines = self.wrap_text(value, max_value_width)
                    for j, line in enumerate(wrapped_lines):
                        if y_pos + j < h - 3:  # Don't go beyond screen
                            value_attr = curses.color_pair(2) if value else curses.color_pair(8)
                            stdscr.addstr(y_pos + j, len(label) + 3, line, value_attr)
                    y_pos += len(wrapped_lines) - 1  # Account for wrapped lines
                else:
                    stdscr.addstr(y_pos, len(label) + 3, "", curses.color_pair(8))
                
                y_pos += 1
            
            # Status line
            if current_field < len(field_names):
                current_field_name = field_names[current_field]
                status = f"Editing: {fields[current_field_name]['label']} | "
                if fields[current_field_name]['required']:
                    status += "Required field"
                else:
                    status += "Optional field"
            else:
                status = "Ready to save"
            
            stdscr.addstr(h-2, 2, status, curses.color_pair(3))
            
            # Save/Cancel hints
            stdscr.addstr(h-1, 2, "\: Save Persona | Esc: Cancel", curses.color_pair(3))
            
            stdscr.refresh()
            
            # Handle input
            key = stdscr.getch()
            
            if key == 27:  # Esc - cancel
                editing = False
            elif key == curses.KEY_UP:
                if current_field > 0:
                    current_field -= 1
            elif key == curses.KEY_DOWN:
                if current_field < len(field_names) - 1:
                    current_field += 1
            elif key == ord('\t'):  # Tab - next field
                if current_field < len(field_names) - 1:
                    current_field += 1
            elif key == ord('\\'):  # \ - save
                # Validate required fields
                valid = True
                error_msg = ""
                
                for field_name in field_names:
                    field = fields[field_name]
                    if field['required'] and not field['value'].strip():
                        valid = False
                        error_msg = f"Required field '{field['label']}' is empty"
                        break
                
                # Validate filename
                if valid and 'filename' in fields:
                    filename = fields['filename']['value'].strip()
                    if not filename:
                        valid = False
                        error_msg = "Filename is required"
                    elif ' ' in filename:
                        valid = False
                        error_msg = "Filename cannot contain spaces"
                
                if valid:
                    self.save_persona(fields)
                    stdscr.addstr(h-2, 2, "Persona saved successfully!", curses.color_pair(2))
                    stdscr.refresh()
                    stdscr.getch()
                    editing = False
                else:
                    stdscr.addstr(h-2, 2, f"Error: {error_msg}", curses.color_pair(3) | curses.A_BOLD)
                    stdscr.refresh()
                    stdscr.getch()
            elif key == ord('\n'):  # Enter - edit field
                if current_field < len(field_names):
                    field_name = field_names[current_field]
                    new_value = self.edit_field_value(stdscr, fields[field_name]['label'], fields[field_name]['value'])
                    if new_value is not None:
                        fields[field_name]['value'] = new_value
    
    def edit_field_value(self, stdscr, field_label, current_value):
        """Edit a single field value with multi-line support"""
        h, w = stdscr.getmaxyx()
        
        # Create a temporary edit window
        edit_height = min(10, h - 10)
        edit_width = w - 10
        edit_win = curses.newwin(edit_height, edit_width, 5, 5)
        edit_win.keypad(True)
        
        # Current editing state
        lines = current_value.split('\n') if current_value else ['']
        cursor_line = 0
        cursor_col = len(lines[-1]) if lines else 0
        editing = True
        
        while editing and self.running:
            edit_win.clear()
            edit_win.border()
            
            # Show field label
            edit_win.addstr(0, 2, field_label, curses.color_pair(1) | curses.A_BOLD)
            
            # Show content with proper wrapping
            content_y = 2
            display_line_count = 0
            for i, line in enumerate(lines):
                if display_line_count >= edit_height - 3:
                    break  # Don't exceed window height
                
                # Wrap long lines
                if len(line) > edit_width - 4:
                    wrapped_lines = self.wrap_text(line, edit_width - 4)
                    for j, wrapped_line in enumerate(wrapped_lines):
                        if display_line_count < edit_height - 3:
                            edit_win.addstr(content_y + display_line_count, 2, wrapped_line)
                            display_line_count += 1
                else:
                    edit_win.addstr(content_y + display_line_count, 2, line)
                    display_line_count += 1
            
            # Position cursor
            if cursor_line < len(lines) and cursor_line < edit_height - 3:
                actual_col = min(cursor_col, len(lines[cursor_line]))
                display_col = min(actual_col, edit_width - 4)
                try:
                    edit_win.move(content_y + cursor_line, 2 + display_col)
                except:
                    pass
            
            # Instructions
            instructions = "Enter: New line | \\: Done | Esc: Cancel | ↑↓: Navigate | ←→: Move cursor"
            edit_win.addstr(edit_height-2, 2, instructions[:edit_width-4], curses.color_pair(3))
            
            edit_win.refresh()
            
            # Handle input
            key = edit_win.getch()
            
            if key == 27:  # Esc - cancel
                return None
            elif key == ord('\\'):  # \ - done
                return '\n'.join(lines)
            elif key == ord('\n'):  # Enter - new line
                # Split current line at cursor position
                current_line = lines[cursor_line]
                before_cursor = current_line[:cursor_col]
                after_cursor = current_line[cursor_col:]
                lines[cursor_line] = before_cursor
                lines.insert(cursor_line + 1, after_cursor)
                cursor_line += 1
                cursor_col = 0
            elif key == curses.KEY_UP:
                if cursor_line > 0:
                    cursor_line -= 1
                    cursor_col = min(cursor_col, len(lines[cursor_line]))
            elif key == curses.KEY_DOWN:
                if cursor_line < len(lines) - 1:
                    cursor_line += 1
                    cursor_col = min(cursor_col, len(lines[cursor_line]))
            elif key == curses.KEY_LEFT:
                if cursor_col > 0:
                    cursor_col -= 1
            elif key == curses.KEY_RIGHT:
                if cursor_col < len(lines[cursor_line]):
                    cursor_col += 1
            elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:  # Backspace
                if cursor_col > 0:
                    lines[cursor_line] = lines[cursor_line][:cursor_col-1] + lines[cursor_line][cursor_col:]
                    cursor_col -= 1
                elif cursor_line > 0:  # Join with previous line
                    cursor_col = len(lines[cursor_line-1])
                    lines[cursor_line-1] += lines[cursor_line]
                    lines.pop(cursor_line)
                    cursor_line -= 1
            elif key == curses.KEY_DC:  # Delete
                if cursor_col < len(lines[cursor_line]):
                    lines[cursor_line] = lines[cursor_line][:cursor_col] + lines[cursor_line][cursor_col+1:]
                elif cursor_line < len(lines) - 1:  # Join with next line
                    lines[cursor_line] += lines[cursor_line+1]
                    lines.pop(cursor_line + 1)
            elif 32 <= key <= 126:  # Printable characters
                char = chr(key)
                lines[cursor_line] = lines[cursor_line][:cursor_col] + char + lines[cursor_line][cursor_col:]
                cursor_col += 1
    
    def save_character(self, fields):
        """Save character data to JSON file"""
        # Prepare character data
        character_data = {
            'name': fields['name']['value'].strip(),
            'age': int(fields['age']['value'].strip()) if fields['age']['value'].strip().isdigit() else 0,
            'title': fields['title']['value'].strip(),
            'basic_info': fields['basic_info']['value'].strip(),
            'personality': fields['personality']['value'].strip(),
            'speech_patterns': [s.strip() for s in fields['speech_patterns']['value'].split(',') if s.strip()],
            'appearance': fields['appearance']['value'].strip(),
            'background': fields['background']['value'].strip(),
            'goals': fields['goals']['value'].strip(),
            'fears': fields['fears']['value'].strip(),
            'scenario': fields['scenario']['value'].strip()
        }
        
        # Generate filename
        filename = fields['filename']['value'].strip()
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Save to file
        filepath = os.path.join(self.character_manager.characters_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(character_data, f, indent=2, ensure_ascii=False)
    
    def save_persona(self, fields):
        """Save persona data to JSON file"""
        # Prepare persona data
        persona_data = {
            'name': fields['name']['value'].strip(),
            'info': fields['info']['value'].strip()
        }
        
        # Generate filename
        filename = fields['filename']['value'].strip()
        if not filename.endswith('.json'):
            filename += '.json'
        
        # Save to file
        filepath = os.path.join(self.persona_manager.personas_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(persona_data, f, indent=2, ensure_ascii=False)

def run_menu_curses():
    """Entry point for menu-driven curses mode"""
    # Load API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Please set GEMINI_API_KEY environment variable")
        return
    
    # Initialize clients
    characters_dir = os.path.join(os.path.dirname(__file__), "characters")
    personas_dir = os.path.join(os.path.dirname(__file__), "personas")
    
    gemini_client = GeminiClient(api_key)
    character_manager = CharacterManager(characters_dir)
    persona_manager = PersonaManager(personas_dir)
    
    # Run menu curses interface
    interface = MenuCursesInterface(gemini_client, character_manager, persona_manager)
    interface.run()
