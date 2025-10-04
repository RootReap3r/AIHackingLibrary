import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import requests
import json
import os
from datetime import datetime
import threading

class OllamaChatGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Ollama Chat Interface")
        self.root.geometry("800x600")
        
        self.base_url = "http://localhost:11434"
        self.current_model = ""
        self.chat_history = []
        self.current_chat_id = None
        self.chats = {}  # Store multiple chats
        
        self.setup_ui()
        self.load_models()
        self.load_saved_chats()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Top frame for model selection and controls
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Model selection
        ttk.Label(top_frame, text="Model:").pack(side=tk.LEFT, padx=(0, 5))
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(top_frame, textvariable=self.model_var, state="readonly")
        self.model_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.model_combo.bind('<<ComboboxSelected>>', self.on_model_select)
        
        # Chat management
        ttk.Button(top_frame, text="New Chat", command=self.new_chat).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(top_frame, text="Saved Chats:").pack(side=tk.LEFT, padx=(20, 5))
        self.chat_var = tk.StringVar()
        self.chat_combo = ttk.Combobox(top_frame, textvariable=self.chat_var, state="readonly")
        self.chat_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.chat_combo.bind('<<ComboboxSelected>>', self.on_chat_select)
        
        ttk.Button(top_frame, text="Delete Chat", command=self.delete_chat).pack(side=tk.LEFT, padx=5)
        
        # File upload button
        ttk.Button(top_frame, text="Upload File", command=self.upload_file).pack(side=tk.RIGHT, padx=5)
        
        # Chat display area
        self.chat_display = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Input area
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X)
        
        self.input_text = tk.Text(input_frame, height=3, wrap=tk.WORD)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.input_text.bind('<Return>', self.on_enter_pressed)
        self.input_text.bind('<Shift-Return>', lambda e: 'break')  # Shift+Enter for new line
        
        # Buttons frame
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.send_button = ttk.Button(button_frame, text="Send", command=self.send_message)
        self.send_button.pack(pady=2)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_generation, state=tk.DISABLED)
        self.stop_button.pack(pady=2)
        
        self.generating = False
        
    def load_models(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [model['name'] for model in data.get('models', [])]
                self.model_combo['values'] = models
                if models:
                    self.model_var.set(models[0])
                    self.current_model = models[0]
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load models: {str(e)}")
    
    def load_saved_chats(self):
        # Create chats directory if it doesn't exist
        if not os.path.exists('chats'):
            os.makedirs('chats')
        
        # Load existing chats
        chat_files = [f for f in os.listdir('chats') if f.endswith('.json')]
        chat_names = [f[:-5] for f in chat_files]  # Remove .json extension
        
        self.chat_combo['values'] = chat_names
        self.new_chat()  # Start with a new chat
    
    def new_chat(self):
        self.current_chat_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        chat_name = f"Chat_{datetime.now().strftime('%H:%M:%S')}"
        self.chats[self.current_chat_id] = {
            'name': chat_name,
            'messages': [],
            'model': self.current_model
        }
        self.chat_var.set(chat_name)
        self.update_chat_combo()
        self.display_chat()
    
    def on_model_select(self, event):
        self.current_model = self.model_var.get()
        if self.current_chat_id:
            self.chats[self.current_chat_id]['model'] = self.current_model
    
    def on_chat_select(self, event):
        selected_chat = self.chat_var.get()
        for chat_id, chat_data in self.chats.items():
            if chat_data['name'] == selected_chat:
                self.current_chat_id = chat_id
                self.current_model = chat_data.get('model', self.current_model)
                self.model_var.set(self.current_model)
                self.display_chat()
                break
    
    def delete_chat(self):
        if not self.current_chat_id:
            return
        
        if messagebox.askyesno("Delete Chat", "Are you sure you want to delete this chat?"):
            # Delete from memory
            del self.chats[self.current_chat_id]
            
            # Delete from disk
            chat_file = f"chats/{self.current_chat_id}.json"
            if os.path.exists(chat_file):
                os.remove(chat_file)
            
            # Create new chat
            self.new_chat()
            self.update_chat_combo()
    
    def update_chat_combo(self):
        chat_names = [chat_data['name'] for chat_data in self.chats.values()]
        self.chat_combo['values'] = chat_names
    
    def upload_file(self):
        filename = filedialog.askopenfilename(
            title="Select file to upload",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                # Add file content to input
                self.input_text.insert(tk.END, f"\n[File: {os.path.basename(filename)}]\n{content}")
                messagebox.showinfo("Success", f"File '{os.path.basename(filename)}' loaded!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to read file: {str(e)}")
    
    def on_enter_pressed(self, event):
        if not event.state & 0x1:  # If Shift is not pressed
            self.send_message()
            return 'break'  # Prevent default behavior
        return None
    
    def send_message(self):
        if self.generating:
            return
        
        message = self.input_text.get(1.0, tk.END).strip()
        if not message or not self.current_model:
            return
        
        # Clear input
        self.input_text.delete(1.0, tk.END)
        
        # Add user message to display
        self.add_to_display("You", message)
        
        # Start generation in thread
        thread = threading.Thread(target=self.generate_response, args=(message,))
        thread.daemon = True
        thread.start()
    
    def stop_generation(self):
        self.generating = False
    
    def generate_response(self, user_message):
        self.generating = True
        self.root.after(0, self.update_buttons, True)
        
        try:
            # Prepare messages for API
            messages = []
            if self.current_chat_id and self.chats[self.current_chat_id]['messages']:
                messages = self.chats[self.current_chat_id]['messages'][-10:]  # Last 10 messages for context
            
            messages.append({"role": "user", "content": user_message})
            
            payload = {
                "model": self.current_model,
                "messages": messages,
                "stream": True
            }
            
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=60
            )
            
            full_response = ""
            self.root.after(0, self.add_to_display, "Assistant", "")
            
            for line in response.iter_lines():
                if not self.generating:
                    break
                    
                if line:
                    try:
                        data = json.loads(line)
                        if 'message' in data and 'content' in data['message']:
                            content = data['message']['content']
                            full_response += content
                            self.root.after(0, self.update_last_message, content)
                    except json.JSONDecodeError:
                        continue
            
            if full_response and self.generating:
                # Save to chat history
                if self.current_chat_id:
                    self.chats[self.current_chat_id]['messages'].extend([
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": full_response}
                    ])
                    self.save_chat()
                
        except Exception as e:
            self.root.after(0, self.add_to_display, "System", f"Error: {str(e)}")
        
        finally:
            self.generating = False
            self.root.after(0, self.update_buttons, False)
    
    def update_buttons(self, generating):
        if generating:
            self.send_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.send_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
    
    def add_to_display(self, sender, message):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"\n{sender}: {message}\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def update_last_message(self, content):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, content)
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def display_chat(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete(1.0, tk.END)
        
        if self.current_chat_id and self.chats[self.current_chat_id]['messages']:
            for msg in self.chats[self.current_chat_id]['messages']:
                role = "You" if msg['role'] == 'user' else "Assistant"
                self.chat_display.insert(tk.END, f"\n{role}: {msg['content']}\n")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def save_chat(self):
        if self.current_chat_id:
            chat_file = f"chats/{self.current_chat_id}.json"
            with open(chat_file, 'w', encoding='utf-8') as f:
                json.dump(self.chats[self.current_chat_id], f, indent=2)
    
    def on_closing(self):
        # Save all chats before closing
        for chat_id in self.chats:
            chat_file = f"chats/{chat_id}.json"
            with open(chat_file, 'w', encoding='utf-8') as f:
                json.dump(self.chats[chat_id], f, indent=2)
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = OllamaChatGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
