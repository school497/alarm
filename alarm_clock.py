#!/usr/bin/env python3
"""
Raspberry Pi Touch Screen Alarm Clock with Apple Music and Tuya Smart Bulb Integration
Frutiger Aero Style Redesign
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import datetime
import json
import os
import webbrowser
from tkinter import font
import requests
import pygame
from tkinterweb import HtmlFrame  # For Apple Music iframe
from tuya_connector import TuyaOpenAPI

class AlarmClockApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Aero Alarm")
        self.root.geometry("800x480")
        self.root.configure(bg='#e0f0ff')  # Light blue background
        self.root.attributes('-fullscreen', True)
        
        # Initialize pygame for alarm sounds
        pygame.mixer.init()
        
        # Configuration
        self.config_file = "alarm_config.json"
        self.load_config()
        
        # Initialize Tuya API
        self.tuya_api = None
        self.init_tuya()
        
        # State variables
        self.current_screen = "lock"
        self.last_activity = time.time()
        self.inactivity_timeout = 300  # 5 minutes
        self.alarms = []
        self.active_alarm = None
        self.snooze_time = 5  # minutes
        
        # Load alarms
        self.load_alarms()
        
        # Create UI elements
        self.create_widgets()
        
        # Start background threads
        self.start_background_tasks()
        
        # Bind events
        self.bind_activity_events()
        
    def load_config(self):
        """Load configuration from JSON file"""
        default_config = {
            "tuya_access_id": "",
            "tuya_access_secret": "",
            "tuya_device_id": "",
            "tuya_endpoint": "https://openapi.tuyaus.com"
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
            except:
                self.config = default_config
        else:
            self.config = default_config
            self.save_config()
    
    def save_config(self):
        """Save configuration to JSON file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def init_tuya(self):
        """Initialize Tuya API connection"""
        try:
            if all([self.config.get("tuya_access_id"), 
                   self.config.get("tuya_access_secret"),
                   self.config.get("tuya_device_id")]):
                self.tuya_api = TuyaOpenAPI(
                    self.config["tuya_endpoint"],
                    self.config["tuya_access_id"],
                    self.config["tuya_access_secret"]
                )
                self.tuya_api.connect()
        except Exception as e:
            print(f"Failed to initialize Tuya API: {e}")
    
    def create_widgets(self):
        """Create all UI widgets in Frutiger Aero style"""
        # Main container
        self.main_frame = tk.Frame(self.root, bg='#e0f0ff')
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create different screens
        self.create_lock_screen()
        self.create_main_screen()
        self.create_alarm_setup_screen()
        self.create_settings_screen()
        self.create_music_screen()
        
        # Show lock screen initially
        self.show_lock_screen()
    
    def create_lock_screen(self):
        """Create lock screen with time and date in Frutiger Aero style"""
        self.lock_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
        
        # Background gradient effect
        self.canvas = tk.Canvas(self.lock_frame, width=800, height=480, bg='#e0f0ff', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Draw gradient circles (Frutiger Aero signature design)
        self.canvas.create_oval(-100, -100, 300, 300, fill='#b8e2ff', outline='')
        self.canvas.create_oval(600, 100, 900, 400, fill='#c8e8ff', outline='')
        self.canvas.create_oval(400, 300, 800, 700, fill='#d0ebff', outline='')
        
        # Time display
        self.time_font = font.Font(family="Segoe UI Light", size=96, weight="normal")
        self.time_label = tk.Label(
            self.canvas,
            text="",
            font=self.time_font,
            fg='#0078d7',  # Windows Vista/7 blue
            bg='#e0f0ff'
        )
        self.time_label.place(relx=0.5, rely=0.4, anchor=tk.CENTER)
        
        # Date display
        self.date_font = font.Font(family="Segoe UI", size=24, weight="normal")
        self.date_label = tk.Label(
            self.canvas,
            text="",
            font=self.date_font,
            fg='#0078d7',
            bg='#e0f0ff'
        )
        self.date_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Tap to unlock (with glossy button effect)
        unlock_btn = tk.Label(
            self.canvas,
            text="Tap to unlock",
            font=font.Font(family="Segoe UI", size=16),
            fg='#ffffff',
            bg='#0078d7',
            bd=0,
            padx=20,
            pady=8,
            relief=tk.RAISED
        )
        unlock_btn.place(relx=0.5, rely=0.7, anchor=tk.CENTER)
        
        # Add glossy effect to button
        unlock_btn.bind("<Enter>", lambda e: unlock_btn.config(bg='#0091ff'))
        unlock_btn.bind("<Leave>", lambda e: unlock_btn.config(bg='#0078d7'))
        
        # Bind touch events
        self.lock_frame.bind("<Button-1>", self.unlock_screen)
        self.time_label.bind("<Button-1>", self.unlock_screen)
        self.date_label.bind("<Button-1>", self.unlock_screen)
        unlock_btn.bind("<Button-1>", self.unlock_screen)
    
    def create_main_screen(self):
        """Create main widget-style screen in Frutiger Aero style"""
        self.main_screen_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
        
        # Header with time
        header_frame = tk.Frame(self.main_screen_frame, bg='#e0f0ff', height=80)
        header_frame.pack(fill=tk.X, padx=20, pady=10)
        header_frame.pack_propagate(False)
        
        self.main_time_label = tk.Label(
            header_frame,
            text="",
            font=font.Font(family="Segoe UI Light", size=48, weight="bold"),
            fg='#0078d7',
            bg='#e0f0ff'
        )
        self.main_time_label.pack(side=tk.LEFT, anchor='w')
        
        # Lock button (glossy)
        lock_btn = tk.Label(
            header_frame,
            text="🔒",
            font=font.Font(size=24),
            bg='#0078d7',
            fg='#ffffff',
            bd=0,
            padx=15,
            pady=5,
            relief=tk.RAISED
        )
        lock_btn.pack(side=tk.RIGHT, anchor='e')
        lock_btn.bind("<Button-1>", lambda e: self.show_lock_screen())
        
        # Widget grid
        widget_frame = tk.Frame(self.main_screen_frame, bg='#e0f0ff')
        widget_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Alarms widget
        self.create_alarms_widget(widget_frame)
        
        # Music widget
        self.create_music_widget(widget_frame)
        
        # Lights widget
        self.create_lights_widget(widget_frame)
        
        # Settings widget
        self.create_settings_widget(widget_frame)
    
    def create_alarms_widget(self, parent):
        """Create alarms widget with glass effect"""
        alarm_widget = tk.Frame(parent, bg='#ffffff', relief=tk.FLAT, bd=0)
        alarm_widget.grid(row=0, column=0, sticky='nsew', padx=5, pady=5, ipadx=10, ipady=10)
        
        # Add glass effect
        alarm_widget.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        tk.Label(
            alarm_widget,
            text="⏰ Alarms",
            font=font.Font(family="Segoe UI", size=18, weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=10)
        
        self.alarm_list_frame = tk.Frame(alarm_widget, bg='#ffffff')
        self.alarm_list_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Add alarm button (glossy)
        add_alarm_btn = tk.Label(
            alarm_widget,
            text="+ Add Alarm",
            font=font.Font(family="Segoe UI", size=14),
            bg='#0078d7',
            fg='#ffffff',
            bd=0,
            padx=20,
            pady=8,
            relief=tk.RAISED
        )
        add_alarm_btn.pack(pady=10)
        add_alarm_btn.bind("<Button-1>", lambda e: self.show_alarm_setup())
        
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
    
    def create_music_widget(self, parent):
        """Create music widget with glass effect"""
        music_widget = tk.Frame(parent, bg='#ffffff', relief=tk.FLAT, bd=0)
        music_widget.grid(row=0, column=1, sticky='nsew', padx=5, pady=5, ipadx=10, ipady=10)
        music_widget.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        tk.Label(
            music_widget,
            text="🎵 Music",
            font=font.Font(family="Segoe UI", size=18, weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=10)
        
        # Music button (glossy red like iTunes)
        music_btn = tk.Label(
            music_widget,
            text="Open Apple Music",
            font=font.Font(family="Segoe UI", size=14),
            bg='#ff2d55',  # Apple Music red
            fg='#ffffff',
            bd=0,
            padx=20,
            pady=8,
            relief=tk.RAISED
        )
        music_btn.pack(pady=20)
        music_btn.bind("<Button-1>", lambda e: self.show_music_screen())
        
        parent.grid_columnconfigure(1, weight=1)
    
    def create_lights_widget(self, parent):
        """Create lights control widget with glass effect"""
        lights_widget = tk.Frame(parent, bg='#ffffff', relief=tk.FLAT, bd=0)
        lights_widget.grid(row=1, column=0, sticky='nsew', padx=5, pady=5, ipadx=10, ipady=10)
        lights_widget.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        tk.Label(
            lights_widget,
            text="💡 Lights",
            font=font.Font(family="Segoe UI", size=18, weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=10)
        
        # Light control buttons (glossy)
        btn_frame = tk.Frame(lights_widget, bg='#ffffff')
        btn_frame.pack(pady=10)
        
        on_btn = tk.Label(
            btn_frame,
            text="ON",
            font=font.Font(family="Segoe UI", size=14, weight="bold"),
            bg='#34c759',  # Apple green
            fg='#ffffff',
            bd=0,
            padx=20,
            pady=8,
            relief=tk.RAISED
        )
        on_btn.pack(side=tk.LEFT, padx=5)
        on_btn.bind("<Button-1>", lambda e: self.control_light(True))
        
        off_btn = tk.Label(
            btn_frame,
            text="OFF",
            font=font.Font(family="Segoe UI", size=14, weight="bold"),
            bg='#ff3b30',  # Apple red
            fg='#ffffff',
            bd=0,
            padx=20,
            pady=8,
            relief=tk.RAISED
        )
        off_btn.pack(side=tk.LEFT, padx=5)
        off_btn.bind("<Button-1>", lambda e: self.control_light(False))
        
        parent.grid_rowconfigure(1, weight=1)
    
    def create_settings_widget(self, parent):
        """Create settings widget with glass effect"""
        settings_widget = tk.Frame(parent, bg='#ffffff', relief=tk.FLAT, bd=0)
        settings_widget.grid(row=1, column=1, sticky='nsew', padx=5, pady=5, ipadx=10, ipady=10)
        settings_widget.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        tk.Label(
            settings_widget,
            text="⚙️ Settings",
            font=font.Font(family="Segoe UI", size=18, weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=10)
        
        # Settings button (glossy)
        settings_btn = tk.Label(
            settings_widget,
            text="Configure",
            font=font.Font(family="Segoe UI", size=14),
            bg='#8e8e93',  # Apple gray
            fg='#ffffff',
            bd=0,
            padx=20,
            pady=8,
            relief=tk.RAISED
        )
        settings_btn.pack(pady=20)
        settings_btn.bind("<Button-1>", lambda e: self.show_settings_screen())
    
    def create_alarm_setup_screen(self):
        """Create alarm setup screen in Frutiger Aero style"""
        self.alarm_setup_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
        
        # Header with glass effect
        header = tk.Frame(self.alarm_setup_frame, bg='#0078d7', height=60)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # Back button (glossy)
        back_btn = tk.Label(
            header,
            text="← Back",
            font=font.Font(family="Segoe UI", size=18),
            bg='#0078d7',
            fg='#ffffff',
            bd=0,
            padx=15,
            pady=5,
            relief=tk.RAISED
        )
        back_btn.pack(side=tk.LEFT, anchor='w', padx=10)
        back_btn.bind("<Button-1>", lambda e: self.show_main_screen())
        
        tk.Label(
            header,
            text="New Alarm",
            font=font.Font(family="Segoe UI", size=24, weight="bold"),
            fg='#ffffff',
            bg='#0078d7'
        ).pack(anchor='center')
        
        # Alarm setup form with glass panel
        form_frame = tk.Frame(self.alarm_setup_frame, bg='#ffffff', relief=tk.FLAT, bd=0)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20, ipadx=10, ipady=10)
        form_frame.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        # Time picker
        time_frame = tk.Frame(form_frame, bg='#ffffff', relief=tk.FLAT, bd=0)
        time_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(
            time_frame,
            text="Time",
            font=font.Font(family="Segoe UI", size=18, weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=10)
        
        time_picker_frame = tk.Frame(time_frame, bg='#ffffff')
        time_picker_frame.pack(pady=10)
        
        # Hour (styled like Vista/7 controls)
        self.hour_var = tk.StringVar(value="07")
        hour_spinbox = tk.Spinbox(
            time_picker_frame,
            from_=0, to=23,
            textvariable=self.hour_var,
            width=3,
            font=font.Font(family="Segoe UI", size=18),
            bg='#ffffff',
            fg='#0078d7',
            highlightbackground='#a0c0e0',
            highlightthickness=1,
            relief=tk.FLAT,
            justify=tk.CENTER,
            format="%02.0f"
        )
        hour_spinbox.pack(side=tk.LEFT, padx=5)
        
        tk.Label(time_picker_frame, text=":", font=font.Font(size=18), bg='#ffffff', fg='#0078d7').pack(side=tk.LEFT)
        
        # Minute
        self.minute_var = tk.StringVar(value="00")
        minute_spinbox = tk.Spinbox(
            time_picker_frame,
            from_=0, to=59,
            textvariable=self.minute_var,
            width=3,
            font=font.Font(family="Segoe UI", size=18),
            bg='#ffffff',
            fg='#0078d7',
            highlightbackground='#a0c0e0',
            highlightthickness=1,
            relief=tk.FLAT,
            justify=tk.CENTER,
            format="%02.0f"
        )
        minute_spinbox.pack(side=tk.LEFT, padx=5)
        
        # Repeat daily checkbox (styled)
        self.repeat_var = tk.BooleanVar()
        repeat_frame = tk.Frame(form_frame, bg='#ffffff')
        repeat_frame.pack(pady=10)
        
        repeat_cb = tk.Checkbutton(
            repeat_frame,
            text="Repeat daily",
            variable=self.repeat_var,
            font=font.Font(family="Segoe UI", size=16),
            fg='#0078d7',
            bg='#ffffff',
            activebackground='#ffffff',
            selectcolor='#e0f0ff'
        )
        repeat_cb.pack(side=tk.LEFT)
        
        # Light control checkbox
        self.light_control_var = tk.BooleanVar()
        light_frame = tk.Frame(form_frame, bg='#ffffff')
        light_frame.pack(pady=10)
        
        light_cb = tk.Checkbutton(
            light_frame,
            text="Turn on lights with alarm",
            variable=self.light_control_var,
            font=font.Font(family="Segoe UI", size=16),
            fg='#0078d7',
            bg='#ffffff',
            activebackground='#ffffff',
            selectcolor='#e0f0ff'
        )
        light_cb.pack(side=tk.LEFT)
        
        # Save button (glossy)
        save_btn = tk.Label(
            form_frame,
            text="Save Alarm",
            font=font.Font(family="Segoe UI", size=18, weight="bold"),
            bg='#0078d7',
            fg='#ffffff',
            bd=0,
            padx=40,
            pady=15,
            relief=tk.RAISED
        )
        save_btn.pack(pady=30)
        save_btn.bind("<Button-1>", lambda e: self.save_alarm())
    
    def create_settings_screen(self):
        """Create settings screen in Frutiger Aero style"""
        self.settings_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
        
        # Header with glass effect
        header = tk.Frame(self.settings_frame, bg='#0078d7', height=60)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # Back button (glossy)
        back_btn = tk.Label(
            header,
            text="← Back",
            font=font.Font(family="Segoe UI", size=18),
            bg='#0078d7',
            fg='#ffffff',
            bd=0,
            padx=15,
            pady=5,
            relief=tk.RAISED
        )
        back_btn.pack(side=tk.LEFT, anchor='w', padx=10)
        back_btn.bind("<Button-1>", lambda e: self.show_main_screen())
        
        tk.Label(
            header,
            text="Settings",
            font=font.Font(family="Segoe UI", size=24, weight="bold"),
            fg='#ffffff',
            bg='#0078d7'
        ).pack(anchor='center')
        
        # Settings form with glass panel
        form_frame = tk.Frame(self.settings_frame, bg='#ffffff', relief=tk.FLAT, bd=0)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20, ipadx=10, ipady=10)
        form_frame.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        # Tuya configuration
        tk.Label(
            form_frame,
            text="Tuya Smart Bulb Configuration",
            font=font.Font(family="Segoe UI", size=18, weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=(0, 20))
        
        # Access ID
        tk.Label(form_frame, text="Access ID:", fg='#0078d7', bg='#ffffff', font=font.Font(family="Segoe UI", size=12)).pack(anchor='w')
        self.access_id_entry = tk.Entry(
            form_frame, 
            width=50, 
            font=font.Font(family="Segoe UI", size=12),
            bg='#ffffff',
            fg='#0078d7',
            highlightbackground='#a0c0e0',
            highlightthickness=1,
            relief=tk.FLAT
        )
        self.access_id_entry.pack(fill=tk.X, pady=(0, 10))
        self.access_id_entry.insert(0, self.config.get("tuya_access_id", ""))
        
        # Access Secret
        tk.Label(form_frame, text="Access Secret:", fg='#0078d7', bg='#ffffff', font=font.Font(family="Segoe UI", size=12)).pack(anchor='w')
        self.access_secret_entry = tk.Entry(
            form_frame, 
            width=50, 
            font=font.Font(family="Segoe UI", size=12),
            bg='#ffffff',
            fg='#0078d7',
            highlightbackground='#a0c0e0',
            highlightthickness=1,
            relief=tk.FLAT,
            show="*"
        )
        self.access_secret_entry.pack(fill=tk.X, pady=(0, 10))
        self.access_secret_entry.insert(0, self.config.get("tuya_access_secret", ""))
        
        # Device ID
        tk.Label(form_frame, text="Device ID:", fg='#0078d7', bg='#ffffff', font=font.Font(family="Segoe UI", size=12)).pack(anchor='w')
        self.device_id_entry = tk.Entry(
            form_frame, 
            width=50, 
            font=font.Font(family="Segoe UI", size=12),
            bg='#ffffff',
            fg='#0078d7',
            highlightbackground='#a0c0e0',
            highlightthickness=1,
            relief=tk.FLAT
        )
        self.device_id_entry.pack(fill=tk.X, pady=(0, 20))
        self.device_id_entry.insert(0, self.config.get("tuya_device_id", ""))
        
        # Save button (glossy)
        save_settings_btn = tk.Label(
            form_frame,
            text="Save Settings",
            font=font.Font(family="Segoe UI", size=16, weight="bold"),
            bg='#0078d7',
            fg='#ffffff',
            bd=0,
            padx=30,
            pady=10,
            relief=tk.RAISED
        )
        save_settings_btn.pack(pady=20)
        save_settings_btn.bind("<Button-1>", lambda e: self.save_settings())
    
    def create_music_screen(self):
        """Create music screen with Apple Music iframe in Frutiger Aero style"""
        self.music_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
        
        # Header with glass effect
        header = tk.Frame(self.music_frame, bg='#0078d7', height=60)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # Back button (glossy)
        back_btn = tk.Label(
            header,
            text="← Back",
            font=font.Font(family="Segoe UI", size=18),
            bg='#0078d7',
            fg='#ffffff',
            bd=0,
            padx=15,
            pady=5,
            relief=tk.RAISED
        )
        back_btn.pack(side=tk.LEFT, anchor='w', padx=10)
        back_btn.bind("<Button-1>", lambda e: self.show_main_screen())
        
        tk.Label(
            header,
            text="Apple Music",
            font=font.Font(family="Segoe UI", size=24, weight="bold"),
            fg='#ffffff',
            bg='#0078d7'
        ).pack(anchor='center')
        
        # Apple Music iframe (using tkinterweb)
        try:
            self.music_browser = HtmlFrame(self.music_frame, width=800, height=420)
            self.music_browser.load_url("https://music.apple.com")
            self.music_browser.pack(fill=tk.BOTH, expand=True)
        except:
            # Fallback if tkinterweb not available
            error_frame = tk.Frame(self.music_frame, bg='#ffffff')
            error_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            tk.Label(
                error_frame,
                text="tkinterweb module required for Apple Music integration",
                font=font.Font(family="Segoe UI", size=16),
                fg='#ff3b30',
                bg='#ffffff'
            ).pack(pady=20)
            
            web_btn = tk.Label(
                error_frame,
                text="Open in Browser",
                font=font.Font(family="Segoe UI", size=18),
                bg='#0078d7',
                fg='#ffffff',
                bd=0,
                padx=40,
                pady=20,
                relief=tk.RAISED
            )
            web_btn.pack(pady=10)
            web_btn.bind("<Button-1>", lambda e: webbrowser.open('https://music.apple.com'))
    
    def show_lock_screen(self):
        """Show lock screen"""
        self.hide_all_screens()
        self.lock_frame.pack(fill=tk.BOTH, expand=True)
        self.current_screen = "lock"
        self.update_activity()
    
    def show_main_screen(self):
        """Show main screen"""
        self.hide_all_screens()
        self.main_screen_frame.pack(fill=tk.BOTH, expand=True)
        self.current_screen = "main"
        self.update_alarm_display()
        self.update_activity()
    
    def show_alarm_setup(self):
        """Show alarm setup screen"""
        self.hide_all_screens()
        self.alarm_setup_frame.pack(fill=tk.BOTH, expand=True)
        self.current_screen = "alarm_setup"
        self.update_activity()
    
    def show_settings_screen(self):
        """Show settings screen"""
        self.hide_all_screens()
        self.settings_frame.pack(fill=tk.BOTH, expand=True)
        self.current_screen = "settings"
        self.update_activity()
    
    def show_music_screen(self):
        """Show music screen"""
        self.hide_all_screens()
        self.music_frame.pack(fill=tk.BOTH, expand=True)
        self.current_screen = "music"
        self.update_activity()
    
    def hide_all_screens(self):
        """Hide all screens"""
        self.lock_frame.pack_forget()
        self.main_screen_frame.pack_forget()
        self.alarm_setup_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.music_frame.pack_forget()
    
    def unlock_screen(self, event=None):
        """Unlock screen and show main screen"""
        self.show_main_screen()
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()
    
    def bind_activity_events(self):
        """Bind activity events to all widgets"""
        def on_activity(event):
            self.update_activity()
        
        # Bind to root window
        self.root.bind("<Motion>", on_activity)
        self.root.bind("<Button-1>", on_activity)
        self.root.bind("<Key>", on_activity)
    
    def save_alarm(self):
        """Save new alarm"""
        hour = int(self.hour_var.get())
        minute = int(self.minute_var.get())
        repeat_daily = self.repeat_var.get()
        light_control = self.light_control_var.get()
        
        alarm = {
            "id": len(self.alarms),
            "hour": hour,
            "minute": minute,
            "repeat_daily": repeat_daily,
            "light_control": light_control,
            "enabled": True,
            "snoozed": False,
            "snooze_until": None
        }
        
        self.alarms.append(alarm)
        self.save_alarms()
        self.show_main_screen()
        messagebox.showinfo("Alarm Saved", f"Alarm set for {hour:02d}:{minute:02d}")
    
    def save_settings(self):
        """Save Tuya settings"""
        self.config["tuya_access_id"] = self.access_id_entry.get()
        self.config["tuya_access_secret"] = self.access_secret_entry.get()
        self.config["tuya_device_id"] = self.device_id_entry.get()
        
        self.save_config()
        self.init_tuya()
        
        messagebox.showinfo("Settings Saved", "Tuya configuration saved successfully!")
    
    def load_alarms(self):
        """Load alarms from file"""
        try:
            if os.path.exists("alarms.json"):
                with open("alarms.json", 'r') as f:
                    self.alarms = json.load(f)
        except:
            self.alarms = []
    
    def save_alarms(self):
        """Save alarms to file"""
        with open("alarms.json", 'w') as f:
            json.dump(self.alarms, f, indent=2)
    
    def update_alarm_display(self):
        """Update alarm display in main screen"""
        # Clear existing alarm displays
        for widget in self.alarm_list_frame.winfo_children():
            widget.destroy()
        
        # Show active alarms
        for alarm in self.alarms:
            if alarm["enabled"]:
                alarm_text = f"{alarm['hour']:02d}:{alarm['minute']:02d}"
                if alarm["repeat_daily"]:
                    alarm_text += " (Daily)"
                if alarm["light_control"]:
                    alarm_text += " 💡"
                
                alarm_frame = tk.Frame(self.alarm_list_frame, bg='#ffffff')
                alarm_frame.pack(fill=tk.X, pady=2)
                
                alarm_label = tk.Label(
                    alarm_frame,
                    text=alarm_text,
                    font=font.Font(family="Segoe UI", size=14),
                    fg='#0078d7',
                    bg='#ffffff'
                )
                alarm_label.pack(side=tk.LEFT)
                
                # Delete button
                del_btn = tk.Label(
                    alarm_frame,
                    text="✕",
                    font=font.Font(size=12),
                    fg='#ff3b30',
                    bg='#ffffff'
                )
                del_btn.pack(side=tk.RIGHT)
                del_btn.bind("<Button-1>", lambda e, a=alarm: self.delete_alarm(a))

    def delete_alarm(self, alarm):
        """Delete an alarm"""
        self.alarms = [a for a in self.alarms if a["id"] != alarm["id"]]
        self.save_alarms()
        self.update_alarm_display()
    
    def control_light(self, turn_on):
        """Control Tuya smart bulb"""
        if not self.tuya_api or not self.config.get("tuya_device_id"):
            messagebox.showerror("Error", "Tuya API not configured")
            return
        
        try:
            commands = [{"code": "switch_led", "value": turn_on}]
            response = self.tuya_api.post(
                f"/v1.0/devices/{self.config['tuya_device_id']}/commands",
                {"commands": commands}
            )
            status = "ON" if turn_on else "OFF"
            if response.get("success"):
                messagebox.showinfo("Light Control", f"Light turned {status}")
            else:
                messagebox.showerror("Error", f"Failed to control light: {response}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to control light: {e}")
    
    def check_alarms(self):
        """Check if any alarms should trigger"""
        current_time = datetime.datetime.now()
        
        for alarm in self.alarms:
            if not alarm["enabled"]:
                continue
            
            # Check if snoozed
            if alarm["snoozed"] and alarm["snooze_until"]:
                snooze_time = datetime.datetime.fromisoformat(alarm["snooze_until"])
                if current_time < snooze_time:
                    continue
                else:
                    alarm["snoozed"] = False
                    alarm["snooze_until"] = None
            
            # Check if alarm time matches
            if (current_time.hour == alarm["hour"] and 
                current_time.minute == alarm["minute"] and
                current_time.second < 5):  # Give 5-second window
                
                self.trigger_alarm(alarm)
    
    def trigger_alarm(self, alarm):
        """Trigger an alarm"""
        self.active_alarm = alarm
        
        # Turn on lights if configured
        if alarm["light_control"]:
            self.control_light(True)
        
        # Play alarm sound
        try:
            # You can replace this with a custom alarm sound file
            pygame.mixer.music.load("alarm_sound.wav")  # Add your alarm sound file
            pygame.mixer.music.play(-1)  # Loop indefinitely
        except:
            # Fallback beep
            print('\a')
        
        # Show alarm dialog
        # Show alarm dialog
        self.show_alarm_alert(alarm)
    
    def show_alarm_alert(self, alarm):
        """Show alarm alert dialog"""
        # Create a top-level window for the alarm
        alarm_window = tk.Toplevel(self.root)
        alarm_window.title("Alarm!")
        alarm_window.geometry("600x300")
        alarm_window.configure(bg='#e0f0ff')
        alarm_window.attributes('-fullscreen', True)
        
        # Make it modal
        alarm_window.grab_set()
        alarm_window.focus_set()
        
        # Alarm time display
        time_font = font.Font(family="Segoe UI Light", size=72, weight="bold")
        time_label = tk.Label(
            alarm_window,
            text=f"{alarm['hour']:02d}:{alarm['minute']:02d}",
            font=time_font,
            fg='#0078d7',
            bg='#e0f0ff'
        )
        time_label.pack(pady=20)
        
        # Alarm message
        msg_label = tk.Label(
            alarm_window,
            text="Time to wake up!",
            font=font.Font(family="Segoe UI", size=24),
            fg='#0078d7',
            bg='#e0f0ff'
        )
        msg_label.pack(pady=10)
        
        # Button frame
        btn_frame = tk.Frame(alarm_window, bg='#e0f0ff')
        btn_frame.pack(pady=30)
        
        # Snooze button (glossy)
        snooze_btn = tk.Label(
            btn_frame,
            text=f"Snooze ({self.snooze_time} min)",
            font=font.Font(family="Segoe UI", size=18),
            bg='#ff9500',  # Orange
            fg='#ffffff',
            bd=0,
            padx=30,
            pady=15,
            relief=tk.RAISED
        )
        snooze_btn.pack(side=tk.LEFT, padx=20)
        snooze_btn.bind("<Button-1>", lambda e: self.snooze_alarm(alarm_window, alarm))
        
        # Stop button (glossy)
        stop_btn = tk.Label(
            btn_frame,
            text="Stop Alarm",
            font=font.Font(family="Segoe UI", size=18),
            bg='#ff3b30',  # Red
            fg='#ffffff',
            bd=0,
            padx=30,
            pady=15,
            relief=tk.RAISED
        )
        stop_btn.pack(side=tk.LEFT, padx=20)
        stop_btn.bind("<Button-1>", lambda e: self.stop_alarm(alarm_window, alarm))
    
    def snooze_alarm(self, alarm_window, alarm):
        """Snooze the alarm"""
        alarm["snoozed"] = True
        snooze_until = datetime.datetime.now() + datetime.timedelta(minutes=self.snooze_time)
        alarm["snooze_until"] = snooze_until.isoformat()
        self.save_alarms()
        
        # Stop alarm sound
        pygame.mixer.music.stop()
        
        # Close alarm window
        alarm_window.destroy()
        
        messagebox.showinfo("Snooze", f"Alarm snoozed for {self.snooze_time} minutes")
    
    def stop_alarm(self, alarm_window, alarm):
        """Stop the alarm"""
        # For non-repeating alarms, disable them
        if not alarm["repeat_daily"]:
            alarm["enabled"] = False
            self.save_alarms()
        
        # Reset snooze status
        alarm["snoozed"] = False
        alarm["snooze_until"] = None
        
        # Stop alarm sound
        pygame.mixer.music.stop()
        
        # Close alarm window
        alarm_window.destroy()
        
        self.update_alarm_display()
    
    def update_time(self):
        """Update time display"""
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%A, %B %d")
        
        # Update lock screen
        if hasattr(self, 'time_label'):
            self.time_label.config(text=time_str)
        if hasattr(self, 'date_label'):
            self.date_label.config(text=date_str)
        
        # Update main screen
        if hasattr(self, 'main_time_label'):
            self.main_time_label.config(text=time_str)
        
        # Check for alarms every minute
        if now.second == 0:
            self.check_alarms()
        
        # Check for inactivity timeout
        if (self.current_screen != "lock" and 
            time.time() - self.last_activity > self.inactivity_timeout):
            self.show_lock_screen()
        
        # Schedule next update
        self.root.after(1000, self.update_time)
    
    def start_background_tasks(self):
        """Start background update tasks"""
        self.update_time()
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AlarmClockApp()
    app.run()