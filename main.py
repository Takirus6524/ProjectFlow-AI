import requests
import json
import random
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
import os
import subprocess
import re
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading

# API Keys - Replace with your own from the services below
AI_BACKENDS = {
    'openai': {
        'name': 'OpenAI ChatGPT (Most Popular)',
        'key': os.getenv('OPENAI_API_KEY', ''),  # Set in environment or .env
        'endpoint': 'https://api.openai.com/v1/chat/completions',
        'model': 'gpt-3.5-turbo',
        'type': 'openai_compatible'
    },
    'mistral': {
        'name': 'Mistral (Open Source & Free)',
        'key': os.getenv('MISTRAL_API_KEY', ''),  # Set in environment or .env
        'endpoint': 'https://api.mistral.ai/v1/chat/completions',
        'model': 'mistral-small-latest',
        'type': 'openai_compatible'
    },
    'google': {
        'name': 'Google Gemini (Very Popular)',
        'key': os.getenv('GEMINI_API_KEY', ''),  # Set in environment or .env
        'endpoint': 'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent',
        'model': 'gemini-pro',
        'type': 'google'
    }
}

class LocalAICodeGenerator:
    def __init__(self, silent=False, selected_backend='mistral'):
        self.available_models = []
        self.current_model = None
        self.history_file = "ai_suggestions.json"
        self.suggestion_history = []
        self.silent = silent
        self.selected_backend = selected_backend  # User's choice
        
        # Check for available backends
        self.backend_status = self.check_backends()
        
        # Load history if exists
        self.load_history()
    
    def check_backends(self) -> Dict:
        """Check available AI backends"""
        status = {}
        
        for backend_name in AI_BACKENDS.keys():
            api_key = AI_BACKENDS[backend_name].get('key', '')
            # Backend available if API key is configured
            status[backend_name] = bool(api_key and api_key.strip())
            if not self.silent:
                backend_info = AI_BACKENDS[backend_name]
                if status[backend_name]:
                    print(f"\u2705 {backend_info['name']} available")
                else:
                    print(f"❌ {backend_info['name']} - API key not configured")
        
        return status
    
    def load_history(self):
        """Load suggestion history from file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.suggestion_history = json.load(f)
        except:
            self.suggestion_history = []
    
    def save_suggestion(self, suggestion: Dict):
        """Save suggestion to history"""
        suggestion['timestamp'] = datetime.now().isoformat()
        self.suggestion_history.append(suggestion)
        
        # Keep only last 50 suggestions
        if len(self.suggestion_history) > 50:
            self.suggestion_history = self.suggestion_history[-50:]
        
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.suggestion_history, f, indent=2)
        except:
            pass
    
    def parse_ai_response(self, response_text: str) -> Dict:
        """Parse AI response into structured format"""
        # Try to extract JSON if present
        json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # Try to find JSON in the response
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, response_text, re.DOTALL)
        if matches:
            try:
                return json.loads(matches[-1])
            except:
                pass
        
        # If no JSON, create a structured response from text
        lines = response_text.strip().split('\n')
        project = {
            'name': 'AI-Generated Project',
            'description': '',
            'technologies': [],
            'difficulty': 'intermediate',
            'duration': '1-2 weeks',
            'features': [],
            'learning_outcomes': []
        }
        
        current_section = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect sections
            if 'name:' in line.lower() or 'project:' in line.lower():
                project['name'] = line.split(':', 1)[-1].strip()
            elif 'description:' in line.lower():
                project['description'] = line.split(':', 1)[-1].strip()
            elif 'technologies:' in line.lower() or 'tech stack:' in line.lower():
                techs = line.split(':', 1)[-1].strip()
                project['technologies'] = [t.strip() for t in techs.split(',')]
            elif 'features:' in line.lower():
                current_section = 'features'
            elif 'learning outcomes:' in line.lower():
                current_section = 'learning_outcomes'
            elif line.startswith('- ') or line.startswith('* '):
                if current_section == 'features':
                    project['features'].append(line[2:].strip())
                elif current_section == 'learning_outcomes':
                    project['learning_outcomes'].append(line[2:].strip())
        
        # If no description was found, use first paragraph
        if not project['description'] and lines:
            project['description'] = lines[0]
        
        return project
    
    def generate_with_openai(self, prompt: str) -> str:
        """Generate using OpenAI ChatGPT API"""
        try:
            backend = AI_BACKENDS['openai']
            headers = {
                "Authorization": f"Bearer {backend['key']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": backend['model'],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1000
            }

            for attempt in range(2):
                try:
                    response = requests.post(backend['endpoint'], headers=headers, json=payload, timeout=30)
                except Exception as e:
                    if attempt == 1:
                        return f"OpenAI error: {str(e)}"
                    time.sleep(1.5)
                    continue

                if response.status_code == 200:
                    result = response.json()
                    return result['choices'][0]['message']['content']
                # Retry on rate limit / transient server errors
                if response.status_code in (429, 500, 502, 503) and attempt == 0:
                    time.sleep(1.5)
                    continue
                return f"OpenAI error: {response.status_code}"

            return "OpenAI error: failed after retries"
        except Exception as e:
            return f"OpenAI error: {str(e)}"
    
    def generate_with_mistral(self, prompt: str) -> str:
        """Generate using Mistral API"""
        try:
            backend = AI_BACKENDS['mistral']
            headers = {
                "Authorization": f"Bearer {backend['key']}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": backend['model'],
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(backend['endpoint'], headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return f"Mistral error: {response.status_code}"
        except Exception as e:
            return f"Mistral error: {str(e)}"
    
    def generate_with_google(self, prompt: str) -> str:
        """Generate using Google Gemini API"""
        try:
            backend = AI_BACKENDS['google']
            
            # Google Gemini uses different API format
            url = f"{backend['endpoint']}?key={backend['key']}"
            headers = {"Content-Type": "application/json"}
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }

            for attempt in range(2):
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=30)
                except Exception as e:
                    if attempt == 1:
                        return f"Google error: {str(e)}"
                    time.sleep(1.5)
                    continue

                if response.status_code == 200:
                    result = response.json()
                    candidates = result.get('candidates', [])
                    if candidates and candidates[0].get('content', {}).get('parts'):
                        text = candidates[0]['content']['parts'][0].get('text', '')
                        if text:
                            return text
                    return "Google error: empty response"
                if response.status_code in (429, 500, 502, 503) and attempt == 0:
                    time.sleep(1.5)
                    continue
                return f"Google error: {response.status_code}"

            return "Google error: failed after retries"
        except Exception as e:
            return f"Google error: {str(e)}"
    
    
    def generate_response(self, prompt: str, backend_name: str = None) -> str:
        """Generate response using selected backend"""
        if not backend_name:
            backend_name = self.selected_backend
        
        if backend_name == 'openai':
            return self.generate_with_openai(prompt)
        elif backend_name == 'mistral':
            return self.generate_with_mistral(prompt)
        elif backend_name == 'google':
            return self.generate_with_google(prompt)
        
        else:
            return self.generate_with_openai(prompt)  # Default to OpenAI
    
    def create_project_prompt(self, user_input: Dict) -> str:
        """Create a prompt for AI based on user preferences"""
        skill_level = user_input.get('skill_level', 'intermediate')
        interests = user_input.get('interests', [])
        time_available = user_input.get('time', 'medium')
        focus_area = user_input.get('focus', 'general')
        
        prompt = f"""Generate a unique programming project idea with the following details:

User Requirements:
- Skill Level: {skill_level}
- Interests: {', '.join(interests) if interests else 'Any'}
- Time Available: {time_available}
- Focus Area: {focus_area}

Please provide a detailed project suggestion in this JSON format:
{{
    "name": "Project Name",
    "description": "Brief description of the project",
    "technologies": ["tech1", "tech2", "tech3"],
    "difficulty": "{skill_level}",
    "estimated_duration": "e.g., 1-2 weeks",
    "key_features": ["feature1", "feature2", "feature3"],
    "learning_outcomes": ["what user will learn"],
    "prerequisites": ["required knowledge"],
    "potential_extensions": ["how to expand the project"],
    "resources": ["suggested resources/tutorials"]
}}

Make the project creative, practical, and educational. The project should be appropriate for the skill level and time constraints.

Project Idea:"""
        
        return prompt
    
    def generate_project_idea(self, user_input: Dict, backend_name: str = None) -> Optional[Dict]:
        """Generate a project idea using selected AI backend"""
        if not backend_name:
            backend_name = self.selected_backend
        
        if not any(self.backend_status.values()):
            return None
        
        if not self.silent:
            backend_info = AI_BACKENDS.get(backend_name, {})
            print(f"\n🤖 Generating AI-powered project idea...")
            print(f"🎯 Using {backend_info.get('name', backend_name)}...")
        
        prompt = self.create_project_prompt(user_input)
        response = self.generate_response(prompt, backend_name)

        def is_error_text(text: str) -> bool:
            lowered = text.lower()
            return ("error" in lowered) or ("429" in lowered) or ("quota" in lowered)

        # Fallback: if selected backend failed and Mistral is configured, retry with Mistral
        if (not response or is_error_text(response)) and backend_name != 'mistral' and self.backend_status.get('mistral'):
            if not self.silent:
                print("Selected backend failed; falling back to Mistral...")
            response = self.generate_response(prompt, 'mistral')
            backend_name = 'mistral'
        
        if response and not is_error_text(response):
            project = self.parse_ai_response(response)
            project['raw_response'] = response
            project['backend_used'] = backend_name
            
            # Save to history
            self.save_suggestion({
                'project': project,
                'user_input': user_input,
                'backend': backend_name
            })
            
            return project
        
        return None
    
    def display_project(self, project: Dict):
        """Display project in a nice format"""
        print("\n" + "="*60)
        print("🤖 AI-GENERATED PROJECT IDEA")
        print("="*60)
        print(f"\n📋 Project Name: {project.get('name', 'Unnamed Project')}")
        print(f"\n📝 Description:")
        print(f"   {project.get('description', 'No description')}")
        
        print(f"\n🛠️  Technologies:")
        for tech in project.get('technologies', []):
            print(f"   • {tech}")
        
        print(f"\n⭐ Key Features:")
        for feature in project.get('key_features', project.get('features', [])):
            print(f"   • {feature}")
        
        print(f"\n🎯 Learning Outcomes:")
        for outcome in project.get('learning_outcomes', []):
            print(f"   • {outcome}")
        
        print(f"\n⏱️  Estimated Duration: {project.get('estimated_duration', project.get('duration', 'Not specified'))}")
        print(f"📊 Difficulty: {project.get('difficulty', 'Not specified')}")
        
        if project.get('prerequisites'):
            print(f"\n📚 Prerequisites:")
            for req in project.get('prerequisites', []):
                print(f"   • {req}")
        
        if project.get('potential_extensions'):
            print(f"\n🚀 Potential Extensions:")
            for ext in project.get('potential_extensions', []):
                print(f"   • {ext}")
        
        if project.get('resources'):
            print(f"\n🔗 Suggested Resources:")
            for resource in project.get('resources', []):
                print(f"   • {resource}")
        
        print("\n" + "="*60)
        print(f"Generated using: {project.get('backend_used', 'Unknown')}")

class AICodeSuggestorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Project Idea Generator")
        self.root.geometry("900x700")
        self.generator = LocalAICodeGenerator(silent=True)  # Silent mode for GUI
        self.current_project = None
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        self.setup_ui()
        self.check_backends_status()
    
    def setup_ui(self):
        """Setup the main UI components"""
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Generate Project
        self.generate_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.generate_tab, text='Generate Project')
        self.setup_generate_tab()
        
        # Tab 2: View History
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text='History')
        self.setup_history_tab()
        
        # Tab 3: Settings
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text='Settings')
        self.setup_settings_tab()
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_generate_tab(self):
        """Setup the project generation tab"""
        # Backend Selector
        backend_frame = ttk.LabelFrame(self.generate_tab, text="AI Backend", padding=10)
        backend_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(backend_frame, text="Select AI Service:").pack(side='left', padx=5)
        self.backend_var = tk.StringVar(value=AI_BACKENDS['mistral']['name'])
        backend_combo = ttk.Combobox(backend_frame, textvariable=self.backend_var, width=30, state='readonly')
        backend_combo['values'] = [AI_BACKENDS[k]['name'] for k in sorted(AI_BACKENDS.keys())]
        backend_combo.pack(side='left', padx=5)
        
        # Input frame
        input_frame = ttk.LabelFrame(self.generate_tab, text="Project Preferences", padding=10)
        input_frame.pack(fill='x', padx=10, pady=10)
        
        # Skill Level
        ttk.Label(input_frame, text="Skill Level:").grid(row=0, column=0, sticky='w', pady=5)
        self.skill_var = tk.StringVar(value='intermediate')
        skill_frame = ttk.Frame(input_frame)
        skill_frame.grid(row=0, column=1, sticky='w', pady=5)
        ttk.Radiobutton(skill_frame, text="Beginner", variable=self.skill_var, value='beginner').pack(side='left', padx=5)
        ttk.Radiobutton(skill_frame, text="Intermediate", variable=self.skill_var, value='intermediate').pack(side='left', padx=5)
        ttk.Radiobutton(skill_frame, text="Advanced", variable=self.skill_var, value='advanced').pack(side='left', padx=5)
        
        # Interests
        ttk.Label(input_frame, text="Interests (comma-separated):").grid(row=1, column=0, sticky='w', pady=5)
        self.interests_entry = ttk.Entry(input_frame, width=50)
        self.interests_entry.grid(row=1, column=1, sticky='w', pady=5)
        self.interests_entry.insert(0, "web development, data science, automation")
        
        # Time Available
        ttk.Label(input_frame, text="Time Available:").grid(row=2, column=0, sticky='w', pady=5)
        self.time_var = tk.StringVar(value='1 week')
        time_combo = ttk.Combobox(input_frame, textvariable=self.time_var, width=30, state='readonly')
        time_combo['values'] = ('weekend', '1 week', 'month', 'open-ended')
        time_combo.grid(row=2, column=1, sticky='w', pady=5)
        
        # Focus Area
        ttk.Label(input_frame, text="Focus Area:").grid(row=3, column=0, sticky='w', pady=5)
        self.focus_var = tk.StringVar(value='general')
        focus_combo = ttk.Combobox(input_frame, textvariable=self.focus_var, width=30, state='readonly')
        focus_combo['values'] = ('learning new technology', 'building portfolio project', 
                                  'solving real-world problem', 'just for fun/experimentation', 'general')
        focus_combo.grid(row=3, column=1, sticky='w', pady=5)
        
        # Generate Button
        btn_frame = ttk.Frame(self.generate_tab)
        btn_frame.pack(fill='x', padx=10, pady=10)
        
        self.generate_btn = ttk.Button(btn_frame, text="🤖 Generate Project Idea", command=self.generate_project)
        self.generate_btn.pack(side='left', padx=5)
        
        ttk.Button(btn_frame, text="🚀 Generate Now", command=self.quick_generate).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear Output", command=self.clear_output).pack(side='left', padx=5)
        
        # Output frame
        output_frame = ttk.LabelFrame(self.generate_tab, text="Generated Project", padding=10)
        output_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, width=80, height=20)
        self.output_text.pack(fill='both', expand=True)
        
        # Export button
        export_frame = ttk.Frame(self.generate_tab)
        export_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(export_frame, text="Export as JSON", command=lambda: self.export_current('json')).pack(side='left', padx=5)
        ttk.Button(export_frame, text="Export as Markdown", command=lambda: self.export_current('md')).pack(side='left', padx=5)
        ttk.Button(export_frame, text="Export as Text", command=lambda: self.export_current('txt')).pack(side='left', padx=5)
    
    def setup_history_tab(self):
        """Setup the history viewing tab"""
        # Controls
        control_frame = ttk.Frame(self.history_tab)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(control_frame, text="Refresh History", command=self.load_history).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Clear History", command=self.clear_history).pack(side='left', padx=5)
        
        # History list
        list_frame = ttk.Frame(self.history_tab)
        list_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Treeview for history
        columns = ('Date', 'Project Name', 'Difficulty', 'Backend')
        self.history_tree = ttk.Treeview(list_frame, columns=columns, show='tree headings', height=15)
        
        self.history_tree.heading('#0', text='#')
        self.history_tree.column('#0', width=50)
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=150)
        
        self.history_tree.pack(side='left', fill='both', expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.history_tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        # Bind selection
        self.history_tree.bind('<<TreeviewSelect>>', self.on_history_select)
        
        # Details frame
        details_frame = ttk.LabelFrame(self.history_tab, text="Project Details", padding=10)
        details_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.history_details = scrolledtext.ScrolledText(details_frame, wrap=tk.WORD, height=10)
        self.history_details.pack(fill='both', expand=True)
    
    def setup_settings_tab(self):
        """Setup the settings tab"""
        # Backend status
        status_frame = ttk.LabelFrame(self.settings_tab, text="Available AI Services", padding=10)
        status_frame.pack(fill='x', padx=10, pady=10)
        
        self.backend_labels = {}
        for i, (key, backend) in enumerate(AI_BACKENDS.items()):
            label = ttk.Label(status_frame, text=f"✅ {backend['name']}")
            label.grid(row=i, column=0, sticky='w', pady=3)
            self.backend_labels[key] = label
        
        # Instructions
        instructions_frame = ttk.LabelFrame(self.settings_tab, text="About This App", padding=10)
        instructions_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        instructions_text = scrolledtext.ScrolledText(instructions_frame, wrap=tk.WORD, height=15)
        instructions_text.pack(fill='both', expand=True)

        instructions = """⚠️ IMPORTANT: ADD YOUR API KEYS

This app supports 3 popular AI services. Add your keys via environment variables (or .env) — the code will read them automatically.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 🔥 OpenAI ChatGPT (Most Popular)
    • Best quality responses
    • Env var: OPENAI_API_KEY
    • Get key: https://platform.openai.com/account/api-keys
    • Model: gpt-3.5-turbo

2. 🚀 Mistral (Open Source & Free)
    • Fast and solid quality
    • Env var: MISTRAL_API_KEY
    • Get key: https://console.mistral.ai/
    • Model: mistral-small-latest

3. 🌐 Google Gemini (Very Popular)
    • Great for creative tasks
    • Env var: GEMINI_API_KEY
    • Get key: https://makersuite.google.com/app/apikey
    • Model: gemini-pro

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HOW TO SET UP (no code edits needed):

1. Obtain your API key from one of the links above
2. Export it in your shell (or add to .env):
   • export OPENAI_API_KEY=your_key_here
   • export MISTRAL_API_KEY=your_key_here
   • export GEMINI_API_KEY=your_key_here
3. Restart the app so it picks up the env vars
4. Select your AI service and generate

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TIPS:

• Default backend is Mistral; switch if you prefer OpenAI/Gemini
• Keep your API keys SECRET and avoid sharing them
• If a service errors, switch to another backend

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        instructions_text.insert('1.0', instructions)
        instructions_text.config(state='disabled')
    
    def get_user_input(self) -> Dict:
        """Get user preferences from GUI"""
        interests_text = self.interests_entry.get().strip()
        interests = [i.strip() for i in interests_text.split(',') if i.strip()]
        
        return {
            'skill_level': self.skill_var.get(),
            'interests': interests,
            'time': self.time_var.get(),
            'focus': self.focus_var.get()
        }
    
    def check_backends_status(self):
        """Check and update backend status"""
        def update_status():
            self.generator.backend_status = self.generator.check_backends()
            
            # Schedule GUI updates on main thread
            def update_gui():
                available = 0
                for backend_key in self.backend_labels.keys():
                    backend_info = AI_BACKENDS[backend_key]
                    if self.generator.backend_status.get(backend_key):
                        self.backend_labels[backend_key].config(text=f"✅ {backend_info['name']}")
                        available += 1
                    else:
                        self.backend_labels[backend_key].config(text=f"❌ {backend_info['name']} (add API key)")
                status_msg = f"{available} / {len(self.backend_labels)} services ready"
                if available == 0:
                    status_msg = "No AI service ready - add a key in AI_BACKENDS"
                self.update_status(status_msg)
            
            self.root.after(0, update_gui)
        
        threading.Thread(target=update_status, daemon=True).start()
    
    def update_status(self, message):
        """Update status bar"""
        self.status_bar.config(text=message)
    
    def generate_project(self):
        """Generate project with user input"""
        if not any(self.generator.backend_status.values()):
            messagebox.showerror("Error", "No AI backend available!")
            return
        
        # Get selected backend from combobox
        selected_text = self.backend_var.get()
        backend_key = None
        for key, backend_info in AI_BACKENDS.items():
            if backend_info['name'] == selected_text:
                backend_key = key
                break
        
        if not backend_key:
            backend_key = 'mistral'  # Default fallback

        # Block generation if the selected backend has no API key configured
        if not self.generator.backend_status.get(backend_key, False):
            messagebox.showerror("Error", f"API key not configured for {AI_BACKENDS[backend_key]['name']}. Please add your key in AI_BACKENDS and restart.")
            return
        
        user_input = self.get_user_input()
        backend_name = AI_BACKENDS[backend_key]['name']
        self.update_status(f"Generating with {backend_name}...")
        self.generate_btn.config(state='disabled')
        
        def generate():
            try:
                project = self.generator.generate_project_idea(user_input, backend_key)
                if project:
                    self.current_project = project
                    self.root.after(0, lambda: self.display_project(project))
                    self.root.after(0, lambda: self.update_status("Project generated successfully!"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Failed to generate project"))
                    self.root.after(0, lambda: self.update_status("Generation failed"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Generation failed: {str(e)}"))
                self.root.after(0, lambda: self.update_status("Error occurred"))
            finally:
                self.root.after(0, lambda: self.generate_btn.config(state='normal'))
        
        threading.Thread(target=generate, daemon=True).start()
    
    def quick_generate(self):
        """Generate with current settings (no reset)"""
        # Just generate with whatever settings are currently selected
        # Don't reset the user's choices!
        self.generate_project()
    
    def clear_output(self):
        """Clear the output text"""
        self.output_text.delete('1.0', tk.END)
        self.current_project = None
    
    def display_project(self, project: Dict):
        """Display project in the output text widget"""
        self.output_text.delete('1.0', tk.END)
        
        output = []
        output.append("="*60)
        output.append("🤖 AI-GENERATED PROJECT IDEA")
        output.append("="*60)
        output.append("")
        output.append(f"📋 Project Name: {project.get('name', 'Unnamed Project')}")
        output.append("")
        output.append("📝 Description:")
        output.append(f"   {project.get('description', 'No description')}")
        output.append("")
        
        if project.get('technologies'):
            output.append("🛠️  Technologies:")
            for tech in project.get('technologies', []):
                output.append(f"   • {tech}")
            output.append("")
        
        if project.get('key_features') or project.get('features'):
            output.append("⭐ Key Features:")
            for feature in project.get('key_features', project.get('features', [])):
                output.append(f"   • {feature}")
            output.append("")
        
        if project.get('learning_outcomes'):
            output.append("🎯 Learning Outcomes:")
            for outcome in project.get('learning_outcomes', []):
                output.append(f"   • {outcome}")
            output.append("")
        
        output.append(f"⏱️  Estimated Duration: {project.get('estimated_duration', project.get('duration', 'Not specified'))}")
        output.append(f"📊 Difficulty: {project.get('difficulty', 'Not specified')}")
        output.append("")
        
        if project.get('prerequisites'):
            output.append("📚 Prerequisites:")
            for req in project.get('prerequisites', []):
                output.append(f"   • {req}")
            output.append("")
        
        if project.get('potential_extensions'):
            output.append("🚀 Potential Extensions:")
            for ext in project.get('potential_extensions', []):
                output.append(f"   • {ext}")
            output.append("")
        
        if project.get('resources'):
            output.append("🔗 Suggested Resources:")
            for resource in project.get('resources', []):
                output.append(f"   • {resource}")
            output.append("")
        
        output.append("="*60)
        output.append(f"Generated using: {project.get('backend_used', 'Unknown')}")
        
        self.output_text.insert('1.0', '\n'.join(output))
    
    def load_history(self):
        """Load and display history"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Load history
        self.generator.load_history()
        
        # Populate tree
        for i, entry in enumerate(reversed(self.generator.suggestion_history), 1):
            project = entry['project']
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime("%Y-%m-%d %H:%M")
            
            self.history_tree.insert('', 'end', iid=str(i-1), text=str(i),
                                   values=(timestamp, 
                                          project.get('name', 'Unnamed')[:30],
                                          project.get('difficulty', 'N/A'),
                                          entry.get('backend', 'N/A')))
        
        self.update_status(f"Loaded {len(self.generator.suggestion_history)} history items")
    
    def on_history_select(self, event):
        """Handle history selection"""
        selection = self.history_tree.selection()
        if selection:
            idx = int(selection[0])
            reversed_history = list(reversed(self.generator.suggestion_history))
            if 0 <= idx < len(reversed_history):
                project = reversed_history[idx]['project']
                
                # Display in details
                self.history_details.delete('1.0', tk.END)
                
                details = []
                details.append(f"Name: {project.get('name', 'N/A')}")
                details.append(f"\nDescription: {project.get('description', 'N/A')}")
                details.append(f"\nTechnologies: {', '.join(project.get('technologies', []))}")
                details.append(f"\nDifficulty: {project.get('difficulty', 'N/A')}")
                details.append(f"\nDuration: {project.get('estimated_duration', 'N/A')}")
                
                if project.get('key_features'):
                    details.append("\n\nKey Features:")
                    for feature in project.get('key_features', []):
                        details.append(f"  • {feature}")
                
                self.history_details.insert('1.0', '\n'.join(details))
    
    def clear_history(self):
        """Clear history after confirmation"""
        if messagebox.askyesno("Confirm", "Clear all history?"):
            self.generator.suggestion_history = []
            try:
                with open(self.generator.history_file, 'w') as f:
                    json.dump([], f)
                self.load_history()
                self.update_status("History cleared")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear history: {e}")
    
    def export_current(self, format_type):
        """Export current project"""
        if not self.current_project:
            messagebox.showwarning("Warning", "No project to export. Generate a project first!")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"project_{timestamp}.{format_type}"
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=f".{format_type}",
            filetypes=[(f"{format_type.upper()} files", f"*.{format_type}"), ("All files", "*.*")],
            initialfile=default_name
        )
        
        if not file_path:
            return
        
        try:
            if format_type == 'json':
                with open(file_path, 'w') as f:
                    json.dump(self.current_project, f, indent=2)
            
            elif format_type == 'txt':
                with open(file_path, 'w') as f:
                    f.write(self.output_text.get('1.0', tk.END))
            
            elif format_type == 'md':
                with open(file_path, 'w') as f:
                    f.write(f"# {self.current_project.get('name', 'Project')}\n\n")
                    f.write(f"**Description**: {self.current_project.get('description', '')}\n\n")
                    f.write(f"**Technologies**: `{', '.join(self.current_project.get('technologies', []))}`\n\n")
                    f.write(f"**Difficulty**: {self.current_project.get('difficulty', '')}\n\n")
                    f.write(f"**Duration**: {self.current_project.get('estimated_duration', '')}\n\n")
                    
                    if self.current_project.get('key_features'):
                        f.write("## Key Features\n\n")
                        for feature in self.current_project.get('key_features', []):
                            f.write(f"- {feature}\n")
                        f.write("\n")
            
            messagebox.showinfo("Success", f"Exported to {file_path}")
            self.update_status(f"Exported to {format_type.upper()}")
        
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = AICodeSuggestorGUI(root)
    
    # Load history on startup
    app.load_history()
    
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)