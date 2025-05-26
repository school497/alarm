#!/usr/bin/env python3
"""
Raspberry Pi Touch Screen Alarm Clock with iPod-Style Music Player and Tuya Smart Bulb Integration
Frutiger Aero Style Redesign with Fish Tank Background
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
from tuya_connector import TuyaOpenAPI
from PIL import Image, ImageTk
import math
import random
import re
import subprocess
import pywhatkit as pwk
from io import BytesIO
import urllib.request
from yt_dlp import YoutubeDL
import vlc
from vlc import State as vlcState

class AlarmClockApp:
    def __init__(self):
        self.root = tk.Tk()
        
        # Get screen dimensions
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Calculate scaling factors relative to design resolution of 800x480
        self.scale_x = self.screen_width / 800
        self.scale_y = self.screen_height / 480
        self.scale_factor = min(self.scale_x, self.scale_y) * 0.8  # Reduced scaling for better fit
        
        # Create dynamic font sizes based on screen resolution
        self.font_sizes = {
            'huge': int(36 * self.scale_factor),
            'large': int(28 * self.scale_factor),
            'medium': int(20 * self.scale_factor),
            'small': int(14 * self.scale_factor),
            'tiny': int(10 * self.scale_factor)
        }
        
        # Create dynamic padding/margins based on screen resolution
        self.padding = {
            'large': int(15 * self.scale_factor),
            'medium': int(10 * self.scale_factor),
            'small': int(5 * self.scale_factor),
            'tiny': int(3 * self.scale_factor)
        }
        
        self.root.title("Aero Alarm")
        self.root.geometry(f"{int(800 * self.scale_factor)}x{int(480 * self.scale_factor)}")
        self.root.configure(bg='#e0f0ff')  # Light blue background
        self.root.attributes('-fullscreen', True)
        
        # Initialize pygame for alarm sounds
        pygame.mixer.init()
        
        # Initialize VLC for music playback
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.current_song_url = None
        self.current_song_title = ""
        self.current_song_artist = ""
        self.current_song_thumbnail = None
        
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
        self.music_frame = None  # Will hold the persistent music iframe

        # Fish tank animation state
        self.bubbles = []
        self.fishes = []
        
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
            "tuya_endpoint": "https://openapi.tuyaus.com",
            "alarm_volume": 1.0,  # Max volume
            "music_volume": 0.7
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
        
        # Create different screens IN THIS SPECIFIC ORDER
        self.create_main_screen()
        self.create_alarm_setup_screen()
        self.create_settings_screen()
        self.create_music_screen()
        self.create_lock_screen()
        
        # Initially hide all frames except lock screen
        self.main_screen_frame.pack_forget()
        self.alarm_setup_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.music_frame.pack_forget()
        
        # Show lock screen initially
        self.show_lock_screen()

    
    def create_lock_screen(self):
        """Create lock screen with full-screen fish tank background"""
        self.lock_frame = tk.Frame(self.main_frame, bg='black')
        self.lock_frame.pack(fill=tk.BOTH, expand=True)
        
        # Fish tank canvas - full screen
        self.fish_tank = tk.Canvas(self.lock_frame, bg='#006994', highlightthickness=0)
        self.fish_tank.pack(fill=tk.BOTH, expand=True)
        
        # Draw fish tank elements after canvas is sized
        self.fish_tank.bind("<Configure>", lambda event: self.draw_fish_tank())
        
        # Create a transparent overlay for time/date/unlock button
        overlay_frame = tk.Frame(self.fish_tank, bg='#006994', bd=0)
        overlay_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Time display - make background transparent
        self.time_font = font.Font(family="Segoe UI Light", size=self.font_sizes['huge'], weight="normal")
        self.time_label = tk.Label(
            overlay_frame,
            text="",
            font=self.time_font,
            fg='white',
            bg='#006994',
            bd=0
        )
        self.time_label.pack(pady=self.padding['medium'])
        
        # Date display - transparent background
        self.date_font = font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="normal")
        self.date_label = tk.Label(
            overlay_frame,
            text="",
            font=self.date_font,
            fg='white',
            bg='#006994',
            bd=0
        )
        self.date_label.pack(pady=self.padding['small'])
        
        # Tap to unlock button
        unlock_btn = tk.Label(
            overlay_frame,
            text="Tap to unlock",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='white',
            bg='#34C759',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        unlock_btn.pack(pady=self.padding['large'])
        
        # Button effects
        unlock_btn.bind("<Enter>", lambda e: unlock_btn.config(bg='#30D158'))
        unlock_btn.bind("<Leave>", lambda e: unlock_btn.config(bg='#34C759'))
        
        # Event bindings
        overlay_frame.bind("<Button-1>", self.unlock_screen)
        self.time_label.bind("<Button-1>", self.unlock_screen)
        self.date_label.bind("<Button-1>", self.unlock_screen)
        unlock_btn.bind("<Button-1>", self.unlock_screen)
        
        # Start animation
        self.animate_fish()
    
    def draw_fish_tank(self):
        """Draw fish tank elements that fill the screen"""
        self.fish_tank.delete("all")  # Clear previous drawings
        
        width = self.fish_tank.winfo_width()
        height = self.fish_tank.winfo_height()
        
        # Tank bottom - takes bottom 20% of screen
        bottom_height = int(height * 0.2)
        self.fish_tank.create_rectangle(0, height-bottom_height, width, height, 
                                    fill='#654321', outline='')
        
        # Plants - distributed across the bottom
        plant_positions = [0.1, 0.3, 0.5, 0.7, 0.9]
        for rel_x in plant_positions:
            x = width * rel_x
            self.fish_tank.create_polygon(
                x, height, 
                x-30, height-bottom_height*2, 
                x, height-bottom_height, 
                x+30, height-bottom_height*3, 
                x+10, height,
                fill='#2E8B57', outline='#1E5A3A'
            )
        
        # Bubbles - distributed across entire width
        self.bubbles = []
        for _ in range(20):  # Reduced number of bubbles
            x = random.randint(50, width-50)  # Random x across width
            y = random.randint(height//2, height-bottom_height)  # Start in middle to bottom
            size = random.randint(3, 15)  # Smaller bubbles
            speed = 1 + random.random() * 2  # Slower speed
            bubble_id = self.fish_tank.create_oval(
                x-size, y-size, x+size, y+size,
                fill='#A0D8EF', outline='white'
            )
            self.bubbles.append({
                'id': bubble_id, 
                'x': x, 
                'y': y, 
                'size': size, 
                'speed': speed
            })
        
        # Fish - distributed throughout the tank
        self.fishes = []
        colors = ['#FF6B6B', '#4ECDC4', '#FFE66D', '#FF9F1C']
        for _ in range(6):  # Reduced number of fish
            x = random.randint(100, width-100)
            y = random.randint(100, height-bottom_height-100)
            size = random.randint(20, 50)  # Smaller fish
            color = random.choice(colors)
            speed = 0.5 + random.random() * 2  # Slower speed
            direction = 1 if random.random() > 0.5 else -1
            fish_parts = self.draw_fish(x, y, size, color, direction)
            self.fishes.append({
                'x': x, 'y': y, 'size': size, 
                'color': color, 'speed': speed, 
                'direction': direction,
                'parts': fish_parts
            })

    def draw_fish(self, x, y, size, color, direction=1):
        """Draw a fish at the given position and return its parts"""
        parts = {}
        
        # Body
        body_width = size
        body_height = size * 0.6
        parts['body'] = self.fish_tank.create_oval(
            x - body_width//2, y - body_height//2,
            x + body_width//2, y + body_height//2,
            fill=color, outline=''
        )
        
        # Tail
        tail_width = size * 0.4
        tail_points = [
            x + (body_width//2 * direction), y,
            x + ((body_width//2 + tail_width) * direction), y - tail_width//2,
            x + ((body_width//2 + tail_width) * direction), y + tail_width//2
        ]
        parts['tail'] = self.fish_tank.create_polygon(
            tail_points,
            fill=color, outline=''
        )
        
        # Eye
        eye_size = size * 0.1
        eye_x = x - (body_width//3 * direction)
        parts['eye'] = self.fish_tank.create_oval(
            eye_x - eye_size//2, y - eye_size//2,
            eye_x + eye_size//2, y + eye_size//2,
            fill='white', outline=''
        )
        parts['pupil'] = self.fish_tank.create_oval(
            eye_x - eye_size//4, y - eye_size//4,
            eye_x + eye_size//4, y + eye_size//4,
            fill='black', outline=''
        )
        
        return parts

    def animate_fish(self):
        """Animate fish and bubbles"""
        if not self.fish_tank.winfo_exists():  # Check if canvas still exists
            return
            
        width = self.fish_tank.winfo_width()
        height = self.fish_tank.winfo_height()
        bottom_height = int(height * 0.2)
        
        # Animate bubbles
        for bubble in self.bubbles:
            self.fish_tank.move(bubble['id'], 0, -bubble['speed'])
            bubble['y'] -= bubble['speed']
            if bubble['y'] < -20:
                bubble['y'] = height
                self.fish_tank.coords(bubble['id'], 
                    bubble['x']-bubble['size'], bubble['y']-bubble['size'],
                    bubble['x']+bubble['size'], bubble['y']+bubble['size'])
        
        # Animate fish
        for fish in self.fishes:
            fish['x'] += fish['speed'] * fish['direction']
            if fish['x'] < 0 or fish['x'] > width:
                fish['direction'] *= -1
                # Flip fish
                for part in fish['parts'].values():
                    self.fish_tank.delete(part)
                fish['parts'] = self.draw_fish(fish['x'], fish['y'], fish['size'], fish['color'], fish['direction'])
            else:
                for part in fish['parts'].values():
                    self.fish_tank.move(part, fish['speed'] * fish['direction'], 0)
        
        self.root.after(50, self.animate_fish)
    
    def create_main_screen(self):
        """Create main widget-style screen in Frutiger Aero style"""
        self.main_screen_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
        
        # Header with time
        header_frame = tk.Frame(self.main_screen_frame, bg='#e0f0ff', height=int(50 * self.scale_factor))
        header_frame.pack(fill=tk.X, padx=self.padding['medium'], pady=self.padding['small'])
        header_frame.pack_propagate(False)
        
        self.main_time_label = tk.Label(
            header_frame,
            text="",
            font=font.Font(family="Segoe UI Light", size=self.font_sizes['large'], weight="bold"),
            fg='#0078d7',
            bg='#e0f0ff'
        )
        self.main_time_label.pack(side=tk.LEFT, anchor='w')
        
        # Lock button (Frutiger Aero green)
        lock_btn = tk.Label(
            header_frame,
            text="🔒",
            font=font.Font(size=self.font_sizes['medium']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['small'],
            pady=self.padding['tiny'],
            relief=tk.RAISED
        )
        lock_btn.pack(side=tk.RIGHT, anchor='e')
        lock_btn.bind("<Button-1>", lambda e: self.show_lock_screen())
        
        # Widget grid
        widget_frame = tk.Frame(self.main_screen_frame, bg='#e0f0ff')
        widget_frame.pack(fill=tk.BOTH, expand=True, padx=self.padding['medium'], pady=self.padding['small'])
        
        # Configure grid
        widget_frame.grid_rowconfigure(0, weight=1)
        widget_frame.grid_rowconfigure(1, weight=1)
        widget_frame.grid_columnconfigure(0, weight=1)
        widget_frame.grid_columnconfigure(1, weight=1)
        
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
        alarm_widget.grid(row=0, column=0, sticky='nsew', padx=self.padding['small'], pady=self.padding['small'], 
                         ipadx=self.padding['small'], ipady=self.padding['small'])
        
        # Add glass effect
        alarm_widget.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        tk.Label(
            alarm_widget,
            text="⏰ Alarms",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=self.padding['small'])
        
        self.alarm_list_frame = tk.Frame(alarm_widget, bg='#ffffff')
        self.alarm_list_frame.pack(fill=tk.BOTH, expand=True, padx=self.padding['small'])
        
        # Add scrollbar if needed
        canvas = tk.Canvas(self.alarm_list_frame, bg='#ffffff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.alarm_list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#ffffff')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add alarm button (Frutiger Aero green)
        add_alarm_btn = tk.Label(
            alarm_widget,
            text="+ Add Alarm",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        add_alarm_btn.pack(pady=self.padding['small'])
        add_alarm_btn.bind("<Button-1>", lambda e: self.show_alarm_setup())
        
        # Store the scrollable frame for adding alarms
        self.alarm_list_scrollable_frame = scrollable_frame
    
    def create_music_widget(self, parent):
        """Create music widget with glass effect"""
        music_widget = tk.Frame(parent, bg='#ffffff', relief=tk.FLAT, bd=0)
        music_widget.grid(row=0, column=1, sticky='nsew', padx=self.padding['small'], pady=self.padding['small'], 
                         ipadx=self.padding['small'], ipady=self.padding['small'])
        music_widget.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        tk.Label(
            music_widget,
            text="🎵 Music",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=self.padding['small'])
        
        # Music button (Frutiger Aero green)
        music_btn = tk.Label(
            music_widget,
            text="Open Music Player",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        music_btn.pack(pady=self.padding['medium'])
        music_btn.bind("<Button-1>", lambda e: self.show_music_screen())
    
    def create_lights_widget(self, parent):
        """Create lights control widget with glass effect"""
        lights_widget = tk.Frame(parent, bg='#ffffff', relief=tk.FLAT, bd=0)
        lights_widget.grid(row=1, column=0, sticky='nsew', padx=self.padding['small'], pady=self.padding['small'], 
                          ipadx=self.padding['small'], ipady=self.padding['small'])
        lights_widget.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        tk.Label(
            lights_widget,
            text="💡 Lights",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=self.padding['small'])
        
        # Light control buttons (Frutiger Aero green)
        btn_frame = tk.Frame(lights_widget, bg='#ffffff')
        btn_frame.pack(pady=self.padding['small'])
        
        on_btn = tk.Label(
            btn_frame,
            text="ON",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        on_btn.pack(side=tk.LEFT, padx=self.padding['small'])
        on_btn.bind("<Button-1>", lambda e: self.control_light(True))
        
        off_btn = tk.Label(
            btn_frame,
            text="OFF",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        off_btn.pack(side=tk.LEFT, padx=self.padding['small'])
        off_btn.bind("<Button-1>", lambda e: self.control_light(False))
    
    def create_settings_widget(self, parent):
        """Create settings widget with glass effect"""
        settings_widget = tk.Frame(parent, bg='#ffffff', relief=tk.FLAT, bd=0)
        settings_widget.grid(row=1, column=1, sticky='nsew', padx=self.padding['small'], pady=self.padding['small'], 
                            ipadx=self.padding['small'], ipady=self.padding['small'])
        settings_widget.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        tk.Label(
            settings_widget,
            text="⚙️ Settings",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=self.padding['small'])
        
        # Settings button (Frutiger Aero green)
        settings_btn = tk.Label(
            settings_widget,
            text="Configure",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        settings_btn.pack(pady=self.padding['medium'])
        settings_btn.bind("<Button-1>", lambda e: self.show_settings_screen())
    
    def create_alarm_setup_screen(self):
        """Create alarm setup screen with radial time picker"""
        self.alarm_setup_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
        
        # Header with glass effect
        header = tk.Frame(self.alarm_setup_frame, bg='#34C759', height=int(50 * self.scale_factor))
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # Back button (Frutiger Aero style)
        back_btn = tk.Label(
            header,
            text="← Back",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['small'],
            pady=self.padding['tiny'],
            relief=tk.RAISED
        )
        back_btn.pack(side=tk.LEFT, anchor='w', padx=self.padding['small'])
        back_btn.bind("<Button-1>", lambda e: self.show_main_screen())
        
        tk.Label(
            header,
            text="New Alarm",
            font=font.Font(family="Segoe UI", size=self.font_sizes['medium'], weight="bold"),
            fg='white',
            bg='#34C759'
        ).pack(anchor='center')
        
        # Alarm setup form with glass panel
        form_frame = tk.Frame(self.alarm_setup_frame, bg='#ffffff', relief=tk.FLAT, bd=0)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=self.padding['medium'], pady=self.padding['medium'], 
                       ipadx=self.padding['small'], ipady=self.padding['small'])
        form_frame.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        # Radial time picker
        time_frame = tk.Frame(form_frame, bg='#ffffff', relief=tk.FLAT, bd=0)
        time_frame.pack(fill=tk.X, pady=self.padding['small'])
        
        tk.Label(
            time_frame,
            text="Time",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=self.padding['small'])
        
        # Create radial time picker
        self.create_radial_time_picker(time_frame)
        
        # Repeat daily checkbox (styled)
        self.repeat_var = tk.BooleanVar()
        repeat_frame = tk.Frame(form_frame, bg='#ffffff')
        repeat_frame.pack(pady=self.padding['small'])
        
        repeat_cb = tk.Checkbutton(
            repeat_frame,
            text="Repeat daily",
            variable=self.repeat_var,
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#0078d7',
            bg='#ffffff',
            activebackground='#ffffff',
            selectcolor='#e0f0ff'
        )
        repeat_cb.pack(side=tk.LEFT)
        
        # Light control checkbox
        self.light_control_var = tk.BooleanVar()
        light_frame = tk.Frame(form_frame, bg='#ffffff')
        light_frame.pack(pady=self.padding['small'])
        
        light_cb = tk.Checkbutton(
            light_frame,
            text="Turn on lights with alarm",
            variable=self.light_control_var,
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#0078d7',
            bg='#ffffff',
            activebackground='#ffffff',
            selectcolor='#e0f0ff'
        )
        light_cb.pack(side=tk.LEFT)
        
        # Save button (Frutiger Aero green)
        save_btn = tk.Label(
            form_frame,
            text="Save Alarm",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        save_btn.pack(pady=self.padding['medium'])
        save_btn.bind("<Button-1>", lambda e: self.save_alarm())
    
    def create_radial_time_picker(self, parent):
        """Create Apple-style radial time picker with Frutiger Aero enhancements"""
        self.radial_frame = tk.Frame(parent, bg='#ffffff')
        self.radial_frame.pack(pady=self.padding['small'])
        
        # Create canvas for radial dial with scaled size
        dial_size = int(220 * self.scale_factor)  # Reduced size for smaller screens
        self.radial_canvas = tk.Canvas(
            self.radial_frame, 
            width=dial_size, 
            height=dial_size, 
            bg='#ffffff', 
            highlightthickness=0
        )
        self.radial_canvas.pack()
        
        # Initialize time variables
        self.hour_var = tk.StringVar(value="12")
        self.minute_var = tk.StringVar(value="00")
        self.am_pm_var = tk.StringVar(value="AM")
        
        # Time display with AM/PM toggle
        time_display_frame = tk.Frame(self.radial_frame, bg='#ffffff')
        time_display_frame.pack(pady=self.padding['small'])
        
        self.time_display_var = tk.StringVar(value="12:00 AM")
        self.time_display = tk.Label(
            time_display_frame,
            textvariable=self.time_display_var,
            font=font.Font(family="Segoe UI", size=self.font_sizes['medium'], weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        )
        self.time_display.pack(side=tk.LEFT)
        
        # AM/PM toggle button (Frutiger Aero style)
        am_pm_btn = tk.Label(
            time_display_frame,
            textvariable=self.am_pm_var,
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['small'],
            pady=self.padding['tiny'],
            relief=tk.RAISED
        )
        am_pm_btn.pack(side=tk.LEFT, padx=self.padding['small'])
        am_pm_btn.bind("<Button-1>", lambda e: self.toggle_am_pm())
        
        # Draw radial dial
        self.draw_radial_dial()
        
        # Digital time input as fallback
        digital_frame = tk.Frame(self.radial_frame, bg='#ffffff')
        digital_frame.pack(pady=self.padding['small'])
        
        tk.Label(digital_frame, text="or enter time:", font=font.Font(family="Segoe UI", size=self.font_sizes['tiny']), 
                fg='#0078d7', bg='#ffffff').pack()
        
        time_entry_frame = tk.Frame(digital_frame, bg='#ffffff')
        time_entry_frame.pack()
        
        # Hour entry
        self.hour_entry = ttk.Spinbox(
            time_entry_frame,
            from_=1, to=12,
            width=2,
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            justify=tk.CENTER
        )
        self.hour_entry.pack(side=tk.LEFT)
        self.hour_entry.set("12")
        
        tk.Label(time_entry_frame, text=":", bg='#ffffff').pack(side=tk.LEFT)
        
        # Minute entry
        self.minute_entry = ttk.Spinbox(
            time_entry_frame,
            from_=0, to=59,
            width=2,
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            justify=tk.CENTER,
            format="%02.0f"
        )
        self.minute_entry.pack(side=tk.LEFT)
        self.minute_entry.set("00")
        
        # Bind events for both key and value changes
        self.hour_entry.bind("<KeyRelease>", self.update_time_from_entry)
        self.minute_entry.bind("<KeyRelease>", self.update_time_from_entry)
        self.hour_entry.bind("<<Increment>>", self.update_time_from_entry)
        self.hour_entry.bind("<<Decrement>>", self.update_time_from_entry)
        self.minute_entry.bind("<<Increment>>", self.update_time_from_entry)
        self.minute_entry.bind("<<Decrement>>", self.update_time_from_entry)
        self.hour_entry.bind("<FocusOut>", self.update_time_from_entry)
        self.minute_entry.bind("<FocusOut>", self.update_time_from_entry)
        self.radial_canvas.bind("<B1-Motion>", self.on_radial_drag)
        self.radial_canvas.bind("<Button-1>", self.on_radial_click)

    def toggle_am_pm(self):
        """Toggle between AM and PM"""
        self.am_pm_var.set("PM" if self.am_pm_var.get() == "AM" else "AM")
        self.update_time_display()

    def update_time_from_entry(self, event=None):
        """Update time from digital entry fields"""
        try:
            hour = int(self.hour_entry.get())
            minute = int(self.minute_entry.get())
            if 1 <= hour <= 12 and 0 <= minute <= 59:
                self.hour_var.set(str(hour))
                self.minute_var.set(str(minute).zfill(2))
                self.update_time_display()
                self.draw_radial_dial()  # Update hand position
        except Exception:
            pass

    def draw_radial_dial(self):
        """Draw the radial dial with hour and minute markers and hand"""
        self.radial_canvas.delete("all")
        dial_size = int(220 * self.scale_factor)  # Reduced size for smaller screens
        center_x, center_y = dial_size // 2, dial_size // 2
        radius = int(90 * self.scale_factor)  # Reduced radius
        
        # Draw outer circle with gradient effect
        for i in range(5):
            r = min(90 + i * 10, 255)
            g = min(150 + i * 10, 255)
            b = min(230 + i * 10, 255)
            self.radial_canvas.create_oval(
                center_x - radius + i, center_y - radius + i,
                center_x + radius - i, center_y + radius - i,
                outline=f'#{r:02x}{g:02x}{b:02x}', width=1
            )
        
        # Draw hour markers with decorative elements
        for hour in range(1, 13):
            angle = math.radians((hour * 30) - 90)
            x = center_x + (radius * 0.75) * math.cos(angle)
            y = center_y + (radius * 0.75) * math.sin(angle)
            
            # Decorative circle behind hour
            self.radial_canvas.create_oval(
                x-12, y-12, x+12, y+12,
                outline='#e0f0ff', fill='#e0f0ff', width=2
            )
            # Hour text
            self.radial_canvas.create_text(
                x, y,
                text=str(hour),
                font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
                fill='#0078d7'
            )
        
        # Draw minute markers (smaller dots)
        for minute in range(0, 60, 5):
            if minute % 15 == 0:  # Skip quarter hours (already marked by hours)
                continue
            angle = math.radians((minute * 6) - 90)
            x = center_x + (radius * 0.85) * math.cos(angle)
            y = center_y + (radius * 0.85) * math.sin(angle)
            self.radial_canvas.create_oval(
                x-3, y-3, x+3, y+3,
                fill='#0078d7', outline=''
            )
        
        # Get current time from variables
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
        except:
            hour = 12
            minute = 0
        
        # Draw hour hand
        hour_angle = math.radians((hour % 12) * 30 + (minute / 2) - 90)
        hour_length = radius * 0.5
        hour_x = center_x + hour_length * math.cos(hour_angle)
        hour_y = center_y + hour_length * math.sin(hour_angle)
        self.radial_canvas.create_line(
            center_x, center_y, hour_x, hour_y,
            fill='#0078d7', width=4, capstyle=tk.ROUND
        )
        
        # Draw minute hand
        minute_angle = math.radians(minute * 6 - 90)
        minute_length = radius * 0.75
        minute_x = center_x + minute_length * math.cos(minute_angle)
        minute_y = center_y + minute_length * math.sin(minute_angle)
        self.radial_canvas.create_line(
            center_x, center_y, minute_x, minute_y,
            fill='#34C759', width=2, capstyle=tk.ROUND
        )
        
        # Draw center cap
        self.radial_canvas.create_oval(
            center_x-5, center_y-5, center_x+5, center_y+5,
            fill='#0078d7', outline=''
        )
        
        # Update the digital display
        self.update_time_display()

    def on_radial_click(self, event):
        """Handle click on radial dial to set time"""
        dial_size = int(220 * self.scale_factor)
        center_x, center_y = dial_size // 2, dial_size // 2
        radius = int(90 * self.scale_factor)
        
        # Calculate angle from center to click position
        dx = event.x - center_x
        dy = event.y - center_y
        angle = math.degrees(math.atan2(dy, dx)) + 90
        if angle < 0:
            angle += 360
        
        # Determine if click was in outer ring (minutes) or inner ring (hours)
        click_radius = math.sqrt(dx*dx + dy*dy)
        if click_radius > radius * 0.6:  # Minute selection
            minute = round(angle / 6) % 60
            self.minute_var.set(str(minute).zfill(2))
        else:  # Hour selection
            hour = round(angle / 30) % 12
            if hour == 0:
                hour = 12
            self.hour_var.set(str(hour))
        
        self.draw_radial_dial()
        self.update_digital_entries()

    def on_radial_drag(self, event):
        """Handle drag on radial dial to set time"""
        self.on_radial_click(event)

    def update_time_display(self):
        """Update the digital time display"""
        time_str = f"{self.hour_var.get()}:{self.minute_var.get()} {self.am_pm_var.get()}"
        self.time_display_var.set(time_str)

    def update_digital_entries(self):
        """Update the digital entry fields from radial selection"""
        self.hour_entry.delete(0, tk.END)
        self.hour_entry.insert(0, self.hour_var.get())
        self.minute_entry.delete(0, tk.END)
        self.minute_entry.insert(0, self.minute_var.get())

    def create_settings_screen(self):
        """Create settings screen with Frutiger Aero styling"""
        self.settings_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
        
        # Header with glass effect
        header = tk.Frame(self.settings_frame, bg='#34C759', height=int(50 * self.scale_factor))
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # Back button (Frutiger Aero style)
        back_btn = tk.Label(
            header,
            text="← Back",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['small'],
            pady=self.padding['tiny'],
            relief=tk.RAISED
        )
        back_btn.pack(side=tk.LEFT, anchor='w', padx=self.padding['small'])
        back_btn.bind("<Button-1>", lambda e: self.show_main_screen())
        
        tk.Label(
            header,
            text="Settings",
            font=font.Font(family="Segoe UI", size=self.font_sizes['medium'], weight="bold"),
            fg='white',
            bg='#34C759'
        ).pack(anchor='center')
        
        # Settings form with glass panel
        form_frame = tk.Frame(self.settings_frame, bg='#ffffff', relief=tk.FLAT, bd=0)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=self.padding['medium'], pady=self.padding['medium'], 
                       ipadx=self.padding['small'], ipady=self.padding['small'])
        form_frame.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        # Create scrollable area
        canvas = tk.Canvas(form_frame, bg='#ffffff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(form_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#ffffff')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Tuya API settings
        tuya_frame = tk.Frame(scrollable_frame, bg='#ffffff')
        tuya_frame.pack(fill=tk.X, pady=self.padding['small'])
        
        tk.Label(
            tuya_frame,
            text="Tuya Smart Bulb Settings",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(anchor='w', pady=self.padding['small'])
        
        # Access ID
        tk.Label(
            tuya_frame,
            text="Access ID:",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(anchor='w')
        
        self.tuya_access_id_entry = tk.Entry(
            tuya_frame,
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            width=30
        )
        self.tuya_access_id_entry.pack(fill=tk.X, pady=self.padding['tiny'])
        self.tuya_access_id_entry.insert(0, self.config.get("tuya_access_id", ""))
        
        # Access Secret
        tk.Label(
            tuya_frame,
            text="Access Secret:",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(anchor='w')
        
        self.tuya_access_secret_entry = tk.Entry(
            tuya_frame,
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            width=30,
            show="*"
        )
        self.tuya_access_secret_entry.pack(fill=tk.X, pady=self.padding['tiny'])
        self.tuya_access_secret_entry.insert(0, self.config.get("tuya_access_secret", ""))
        
        # Device ID
        tk.Label(
            tuya_frame,
            text="Device ID:",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(anchor='w')
        
        self.tuya_device_id_entry = tk.Entry(
            tuya_frame,
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            width=30
        )
        self.tuya_device_id_entry.pack(fill=tk.X, pady=self.padding['tiny'])
        self.tuya_device_id_entry.insert(0, self.config.get("tuya_device_id", ""))
        
        # Volume settings
        volume_frame = tk.Frame(scrollable_frame, bg='#ffffff')
        volume_frame.pack(fill=tk.X, pady=self.padding['small'])
        
        tk.Label(
            volume_frame,
            text="Volume Settings",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(anchor='w', pady=self.padding['small'])
        
        # Alarm volume
        tk.Label(
            volume_frame,
            text="Alarm Volume:",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(anchor='w')
        
        self.alarm_volume_slider = tk.Scale(
            volume_frame,
            from_=0, to=100,
            orient=tk.HORIZONTAL,
            length=int(200 * self.scale_factor),
            bg='#ffffff',
            fg='#0078d7',
            highlightthickness=0,
            troughcolor='#e0f0ff',
            activebackground='#34C759'
        )
        self.alarm_volume_slider.pack(anchor='w', pady=self.padding['tiny'])
        self.alarm_volume_slider.set(self.config.get("alarm_volume", 1.0) * 100)
        
        # Music volume
        tk.Label(
            volume_frame,
            text="Music Volume:",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(anchor='w')
        
        self.music_volume_slider = tk.Scale(
            volume_frame,
            from_=0, to=100,
            orient=tk.HORIZONTAL,
            length=int(200 * self.scale_factor),
            bg='#ffffff',
            fg='#0078d7',
            highlightthickness=0,
            troughcolor='#e0f0ff',
            activebackground='#34C759'
        )
        self.music_volume_slider.pack(anchor='w', pady=self.padding['tiny'])
        self.music_volume_slider.set(self.config.get("music_volume", 0.7) * 100)
        
        # Save button (Frutiger Aero green)
        save_btn = tk.Label(
            scrollable_frame,
            text="Save Settings",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        save_btn.pack(pady=self.padding['medium'])
        save_btn.bind("<Button-1>", lambda e: self.save_settings())

    def create_music_screen(self):
        """Create music player screen with iPod-style interface"""
        self.music_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
        
        # Header with glass effect
        header = tk.Frame(self.music_frame, bg='#34C759', height=int(50 * self.scale_factor))
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # Back button (Frutiger Aero style)
        back_btn = tk.Label(
            header,
            text="← Back",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['small'],
            pady=self.padding['tiny'],
            relief=tk.RAISED
        )
        back_btn.pack(side=tk.LEFT, anchor='w', padx=self.padding['small'])
        back_btn.bind("<Button-1>", lambda e: self.show_main_screen())
        
        tk.Label(
            header,
            text="Music Player",
            font=font.Font(family="Segoe UI", size=self.font_sizes['medium'], weight="bold"),
            fg='white',
            bg='#34C759'
        ).pack(anchor='center')
        
        # Music player content with glass panel
        content_frame = tk.Frame(self.music_frame, bg='#ffffff', relief=tk.FLAT, bd=0)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=self.padding['medium'], pady=self.padding['medium'], 
                         ipadx=self.padding['small'], ipady=self.padding['small'])
        content_frame.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        # Album art display
        self.album_art_label = tk.Label(
            content_frame,
            bg='#ffffff',
            width=int(200 * self.scale_factor),
            height=int(200 * self.scale_factor)
        )
        self.album_art_label.pack(pady=self.padding['medium'])
        
        # Default album art (placeholder)
        self.set_default_album_art()
        
        # Song info
        self.song_title_label = tk.Label(
            content_frame,
            text="No song selected",
            font=font.Font(family="Segoe UI", size=self.font_sizes['medium'], weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        )
        self.song_title_label.pack(pady=self.padding['tiny'])
        
        self.song_artist_label = tk.Label(
            content_frame,
            text="",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#0078d7',
            bg='#ffffff'
        )
        self.song_artist_label.pack(pady=self.padding['tiny'])
        
        # Progress bar
        self.progress_frame = tk.Frame(content_frame, bg='#ffffff')
        self.progress_frame.pack(fill=tk.X, padx=self.padding['medium'], pady=self.padding['medium'])
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            orient=tk.HORIZONTAL,
            length=int(250 * self.scale_factor),
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X)
        
        # Time labels
        time_frame = tk.Frame(content_frame, bg='#ffffff')
        time_frame.pack(fill=tk.X, padx=self.padding['medium'])
        
        self.current_time_label = tk.Label(
            time_frame,
            text="0:00",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#0078d7',
            bg='#ffffff'
        )
        self.current_time_label.pack(side=tk.LEFT)
        
        self.total_time_label = tk.Label(
            time_frame,
            text="0:00",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#0078d7',
            bg='#ffffff'
        )
        self.total_time_label.pack(side=tk.RIGHT)
        
        # Controls frame
        controls_frame = tk.Frame(content_frame, bg='#ffffff')
        controls_frame.pack(pady=self.padding['medium'])
        
        # Previous button
        prev_btn = tk.Label(
            controls_frame,
            text="⏮",
            font=font.Font(size=self.font_sizes['large']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        prev_btn.grid(row=0, column=0, padx=self.padding['small'])
        prev_btn.bind("<Button-1>", lambda e: self.prev_song())
        
        # Play/Pause button
        self.play_pause_btn = tk.Label(
            controls_frame,
            text="⏸",
            font=font.Font(size=self.font_sizes['large']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        self.play_pause_btn.grid(row=0, column=1, padx=self.padding['small'])
        self.play_pause_btn.bind("<Button-1>", lambda e: self.toggle_play_pause())
        
        # Next button
        next_btn = tk.Label(
            controls_frame,
            text="⏭",
            font=font.Font(size=self.font_sizes['large']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        next_btn.grid(row=0, column=2, padx=self.padding['small'])
        next_btn.bind("<Button-1>", lambda e: self.next_song())
        
        # Search frame
        search_frame = tk.Frame(content_frame, bg='#ffffff')
        search_frame.pack(fill=tk.X, padx=self.padding['medium'], pady=self.padding['medium'])
        
        self.search_entry = tk.Entry(
            search_frame,
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            width=30
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        search_btn = tk.Label(
            search_frame,
            text="🔍",
            font=font.Font(size=self.font_sizes['small']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        search_btn.pack(side=tk.LEFT, padx=self.padding['small'])
        search_btn.bind("<Button-1>", lambda e: self.search_music())
        
        # Search results frame
        self.search_results_frame = tk.Frame(content_frame, bg='#ffffff')
        self.search_results_frame.pack(fill=tk.BOTH, expand=True, padx=self.padding['medium'], pady=self.padding['small'])
        
        # Create scrollable results area
        results_canvas = tk.Canvas(self.search_results_frame, bg='#ffffff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.search_results_frame, orient="vertical", command=results_canvas.yview)
        self.scrollable_results_frame = tk.Frame(results_canvas, bg='#ffffff')
        
        self.scrollable_results_frame.bind(
            "<Configure>",
            lambda e: results_canvas.configure(
                scrollregion=results_canvas.bbox("all")
            )
        )
        
        results_canvas.create_window((0, 0), window=self.scrollable_results_frame, anchor="nw")
        results_canvas.configure(yscrollcommand=scrollbar.set)
        
        results_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def set_default_album_art(self):
        """Set default album art (placeholder)"""
        # Create a simple gradient image
        width = int(200 * self.scale_factor)
        height = int(200 * self.scale_factor)
        image = Image.new("RGB", (width, height))
        pixels = image.load()
        
        for x in range(width):
            for y in range(height):
                # Gradient from light blue to white
                r = 224 + int(31 * x / width)
                g = 240 + int(15 * y / height)
                b = 255
                pixels[x, y] = (r, g, b)
        
        # Add a music note icon
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        note_size = int(width * 0.3)
        draw.ellipse([(width//2 - note_size//2, height//2 - note_size//2),
                     (width//2 + note_size//2, height//2 + note_size//2)],
                     outline='#0078d7', width=3)
        
        self.default_album_art = ImageTk.PhotoImage(image)
        self.album_art_label.config(image=self.default_album_art)

    def show_lock_screen(self):
        """Show the lock screen"""
        self.current_screen = "lock"
        self.lock_frame.pack(fill=tk.BOTH, expand=True)
        self.main_screen_frame.pack_forget()
        self.alarm_setup_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.music_frame.pack_forget()
        self.last_activity = time.time()  # Reset inactivity timer
        
        # Start updating time on lock screen
        self.update_lock_time()

    def update_lock_time(self):
        """Update time and date on lock screen"""
        if self.current_screen != "lock":
            return
            
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p").lstrip("0")
        date_str = now.strftime("%A, %B %d")
        
        self.time_label.config(text=time_str)
        self.date_label.config(text=date_str)
        
        # Update main screen time as well
        if hasattr(self, 'main_time_label'):
            self.main_time_label.config(text=time_str)
        
        # Schedule next update
        self.root.after(1000, self.update_lock_time)

    def unlock_screen(self, event=None):
        """Unlock the screen and show main interface"""
        self.show_main_screen()

    def show_main_screen(self):
        """Show the main widget screen"""
        self.current_screen = "main"
        self.main_screen_frame.pack(fill=tk.BOTH, expand=True)
        self.lock_frame.pack_forget()
        self.alarm_setup_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.music_frame.pack_forget()
        self.last_activity = time.time()  # Reset inactivity timer
        
        # Update alarm list
        self.update_alarm_list()
        
        # Start updating time if not already running
        if not hasattr(self, 'main_time_label') or not self.main_time_label.winfo_exists():
            self.update_lock_time()

    def show_alarm_setup(self):
        """Show the alarm setup screen"""
        self.current_screen = "alarm_setup"
        self.alarm_setup_frame.pack(fill=tk.BOTH, expand=True)
        self.lock_frame.pack_forget()
        self.main_screen_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.music_frame.pack_forget()
        self.last_activity = time.time()  # Reset inactivity timer
        
        # Reset form fields
        self.hour_var.set("12")
        self.minute_var.set("00")
        self.am_pm_var.set("AM")
        self.repeat_var.set(False)
        self.light_control_var.set(False)
        self.update_time_display()
        self.draw_radial_dial()

    def show_settings_screen(self):
        """Show the settings screen"""
        self.current_screen = "settings"
        self.settings_frame.pack(fill=tk.BOTH, expand=True)
        self.lock_frame.pack_forget()
        self.main_screen_frame.pack_forget()
        self.alarm_setup_frame.pack_forget()
        self.music_frame.pack_forget()
        self.last_activity = time.time()  # Reset inactivity timer

    def show_music_screen(self):
        """Show the music player screen"""
        self.current_screen = "music"
        self.music_frame.pack(fill=tk.BOTH, expand=True)
        self.lock_frame.pack_forget()
        self.main_screen_frame.pack_forget()
        self.alarm_setup_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.last_activity = time.time()  # Reset inactivity timer
        
        # Update player state if music is playing
        if self.player.is_playing():
            self.play_pause_btn.config(text="⏸")
        else:
            self.play_pause_btn.config(text="▶️")

    def update_alarm_list(self):
        """Update the list of alarms in the main screen"""
        # Clear existing alarms
        for widget in self.alarm_list_scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.alarms:
            tk.Label(
                self.alarm_list_scrollable_frame,
                text="No alarms set",
                font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
                fg='#0078d7',
                bg='#ffffff'
            ).pack(pady=self.padding['small'])
            return
        
        # Sort alarms by time
        sorted_alarms = sorted(self.alarms, key=lambda x: (x['time'], x['repeat']))
        
        for alarm in sorted_alarms:
            alarm_frame = tk.Frame(self.alarm_list_scrollable_frame, bg='#ffffff')
            alarm_frame.pack(fill=tk.X, pady=self.padding['tiny'])
            
            # Time label
            time_str = alarm['time'].strftime("%I:%M %p").lstrip("0")
            tk.Label(
                alarm_frame,
                text=time_str,
                font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight="bold"),
                fg='#0078d7',
                bg='#ffffff'
            ).pack(side=tk.LEFT, padx=self.padding['small'])
            
            # Repeat indicator
            repeat_text = "Daily" if alarm['repeat'] else "Once"
            tk.Label(
                alarm_frame,
                text=repeat_text,
                font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
                fg='#0078d7',
                bg='#ffffff'
            ).pack(side=tk.LEFT, padx=self.padding['small'])
            
            # Light control indicator
            if alarm.get('light_control', False):
                tk.Label(
                    alarm_frame,
                text="💡",
                font=font.Font(size=self.font_sizes['small']),
                fg='#0078d7',
                bg='#ffffff'
            ).pack(side=tk.LEFT, padx=self.padding['small'])
            
            # Delete button (Frutiger Aero red)
            delete_btn = tk.Label(
                alarm_frame,
                text="✕",
                font=font.Font(size=self.font_sizes['small']),
                bg='#FF3B30',
                fg='white',
                bd=0,
                padx=self.padding['tiny'],
                pady=self.padding['tiny'],
                relief=tk.RAISED
            )
            delete_btn.pack(side=tk.RIGHT, padx=self.padding['small'])
            delete_btn.bind("<Button-1>", lambda e, a=alarm: self.delete_alarm(a))
            
            # Button effects
            delete_btn.bind("<Enter>", lambda e, b=delete_btn: b.config(bg='#FF453A'))
            delete_btn.bind("<Leave>", lambda e, b=delete_btn: b.config(bg='#FF3B30'))

    def save_alarm(self):
        """Save the new alarm from the setup screen"""
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            am_pm = self.am_pm_var.get()
            
            # Convert to 24-hour format
            if am_pm == "PM" and hour != 12:
                hour += 12
            elif am_pm == "AM" and hour == 12:
                hour = 0
                
            # Create time object
            alarm_time = datetime.time(hour, minute)
            
            # Create alarm dictionary
            alarm = {
                'time': alarm_time,
                'repeat': self.repeat_var.get(),
                'light_control': self.light_control_var.get(),
                'active': True
            }
            
            # Add to alarms list
            self.alarms.append(alarm)
            
            # Save alarms
            self.save_alarms()
            
            # Return to main screen
            self.show_main_screen()
            
        except Exception as e:
            messagebox.showerror("Error", f"Invalid time: {e}")

    def delete_alarm(self, alarm):
        """Delete an alarm from the list"""
        self.alarms.remove(alarm)
        self.save_alarms()
        self.update_alarm_list()

    def save_alarms(self):
        """Save alarms to config file"""
        # Convert time objects to strings for JSON serialization
        alarms_to_save = []
        for alarm in self.alarms:
            alarm_copy = alarm.copy()
            alarm_copy['time'] = alarm['time'].strftime("%H:%M")
            alarms_to_save.append(alarm_copy)
        
        self.config['alarms'] = alarms_to_save
        self.save_config()

    def load_alarms(self):
        """Load alarms from config file"""
        if 'alarms' in self.config:
            self.alarms = []
            for alarm in self.config['alarms']:
                try:
                    # Convert string time back to time object
                    time_obj = datetime.datetime.strptime(alarm['time'], "%H:%M").time()
                    alarm['time'] = time_obj
                    self.alarms.append(alarm)
                except:
                    continue

    def save_settings(self):
        """Save settings from the settings screen"""
        self.config['tuya_access_id'] = self.tuya_access_id_entry.get()
        self.config['tuya_access_secret'] = self.tuya_access_secret_entry.get()
        self.config['tuya_device_id'] = self.tuya_device_id_entry.get()
        self.config['alarm_volume'] = self.alarm_volume_slider.get() / 100
        self.config['music_volume'] = self.music_volume_slider.get() / 100
        
        self.save_config()
        
        # Reinitialize Tuya API with new credentials
        self.init_tuya()
        
        # Show confirmation and return to main screen
        messagebox.showinfo("Settings Saved", "Your settings have been saved.")
        self.show_main_screen()

    def control_light(self, on):
        """Control the Tuya smart bulb"""
        if not self.tuya_api:
            messagebox.showerror("Error", "Tuya API not initialized. Check your settings.")
            return
            
        try:
            device_id = self.config.get("tuya_device_id")
            if not device_id:
                messagebox.showerror("Error", "No device ID configured.")
                return
                
            commands = {
                "commands": [
                    {"code": "switch_led", "value": on},
                    {"code": "work_mode", "value": "white"}
                ]
            }
            
            response = self.tuya_api.post(f"/v1.0/iot-03/devices/{device_id}/commands", commands)
            
            if not response.get('success', False):
                messagebox.showerror("Error", f"Failed to control light: {response}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to control light: {e}")

    def check_alarms(self):
        """Check if any alarms should trigger"""
        now = datetime.datetime.now().time()
        
        for alarm in self.alarms:
            if not alarm['active']:
                continue
                
            # Compare hours and minutes
            if now.hour == alarm['time'].hour and now.minute == alarm['time'].minute:
                # Check if this is a one-time alarm that has already triggered today
                if not alarm['repeat'] and alarm.get('triggered_today', False):
                    continue
                    
                # Trigger alarm
                self.trigger_alarm(alarm)
                
                # Mark as triggered if it's a one-time alarm
                if not alarm['repeat']:
                    alarm['triggered_today'] = True
                    self.save_alarms()

    def trigger_alarm(self, alarm):
        """Trigger the alarm with sound and light"""
        self.active_alarm = alarm
        
        # Turn on lights if configured
        if alarm.get('light_control', False):
            self.control_light(True)
        
        # Play alarm sound
        self.play_alarm_sound()
        
        # Show alarm screen
        self.show_alarm_alert()

    def play_alarm_sound(self):
        """Play the alarm sound"""
        try:
            # Use a simple beep sound (you can replace this with an actual sound file)
            pygame.mixer.music.stop()
            pygame.mixer.music.load(self.get_alarm_sound())
            pygame.mixer.music.set_volume(self.config.get('alarm_volume', 1.0))
            pygame.mixer.music.play(loops=-1)  # Loop indefinitely
        except Exception as e:
            print(f"Error playing alarm sound: {e}")
            # Fallback to system beep
            self.root.bell()

    def get_alarm_sound(self):
        """Get the path to the alarm sound file"""
        # Default to a simple beep if no sound file is found
        return "alarm.wav" if os.path.exists("alarm.wav") else None

    def show_alarm_alert(self):
        """Show the alarm alert screen"""
        # Create alarm alert frame if it doesn't exist
        if not hasattr(self, 'alarm_alert_frame'):
            self.create_alarm_alert_frame()
        
        # Update time display
        time_str = self.active_alarm['time'].strftime("%I:%M %p").lstrip("0")
        self.alarm_time_label.config(text=time_str)
        
        # Show the frame and hide others
        self.current_screen = "alarm_alert"
        self.alarm_alert_frame.pack(fill=tk.BOTH, expand=True)
        self.lock_frame.pack_forget()
        self.main_screen_frame.pack_forget()
        self.alarm_setup_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.music_frame.pack_forget()
        self.last_activity = time.time()  # Reset inactivity timer

    def create_alarm_alert_frame(self):
        """Create the alarm alert screen"""
        self.alarm_alert_frame = tk.Frame(self.main_frame, bg='#FF3B30')  # Frutiger Aero red
        
        # Main content
        content_frame = tk.Frame(self.alarm_alert_frame, bg='#FF3B30')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=self.padding['large'], pady=self.padding['large'])
        
        # Alarm time
        self.alarm_time_label = tk.Label(
            content_frame,
            text="",
            font=font.Font(family="Segoe UI Light", size=self.font_sizes['huge'], weight="bold"),
            fg='white',
            bg='#FF3B30'
        )
        self.alarm_time_label.pack(pady=self.padding['large'])
        
        # Alarm message
        tk.Label(
            content_frame,
            text="ALARM!",
            font=font.Font(family="Segoe UI", size=self.font_sizes['large'], weight="bold"),
            fg='white',
            bg='#FF3B30'
        ).pack(pady=self.padding['small'])
        
        # Button frame
        button_frame = tk.Frame(content_frame, bg='#FF3B30')
        button_frame.pack(pady=self.padding['large'])
        
        # Snooze button (Frutiger Aero blue)
        snooze_btn = tk.Label(
            button_frame,
            text=f"Snooze ({self.snooze_time} min)",
            font=font.Font(family="Segoe UI", size=self.font_sizes['medium']),
            bg='#0078d7',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        snooze_btn.pack(side=tk.LEFT, padx=self.padding['medium'])
        snooze_btn.bind("<Button-1>", lambda e: self.snooze_alarm())
        
        # Dismiss button (Frutiger Aero green)
        dismiss_btn = tk.Label(
            button_frame,
            text="Dismiss",
            font=font.Font(family="Segoe UI", size=self.font_sizes['medium']),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=self.padding['medium'],
            pady=self.padding['small'],
            relief=tk.RAISED
        )
        dismiss_btn.pack(side=tk.LEFT, padx=self.padding['medium'])
        dismiss_btn.bind("<Button-1>", lambda e: self.dismiss_alarm())

    def snooze_alarm(self):
        """Snooze the current alarm"""
        # Stop alarm sound
        pygame.mixer.music.stop()
        
        # Calculate snooze time
        snooze_time = datetime.datetime.now() + datetime.timedelta(minutes=self.snooze_time)
        
        # Create a temporary snooze alarm
        self.alarms.append({
            'time': snooze_time.time(),
            'repeat': False,
            'light_control': self.active_alarm.get('light_control', False),
            'active': True,
            'is_snooze': True
        })
        
        # Save alarms
        self.save_alarms()
        
        # Hide alarm alert frame and show main screen
        self.alarm_alert_frame.pack_forget()
        self.show_main_screen()
        
        self.active_alarm = None

    def dismiss_alarm(self):
        """Dismiss the current alarm"""
        # Stop alarm sound
        pygame.mixer.music.stop()
        
        # Turn off lights if they were turned on by this alarm
        if self.active_alarm.get('light_control', False):
            self.control_light(False)
        
        # If this was a one-time alarm, deactivate it
        if not self.active_alarm.get('repeat', False) and not self.active_alarm.get('is_snooze', False):
            self.active_alarm['active'] = False
            self.save_alarms()
        
        # Hide alarm alert frame and show main screen
        self.alarm_alert_frame.pack_forget()
        self.show_main_screen()
        
        self.active_alarm = None

    def search_music(self):
        """Search for music on YouTube"""
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showinfo("Info", "Please enter a search term")
            return
            
        try:
            # Clear previous results
            for widget in self.scrollable_results_frame.winfo_children():
                widget.destroy()
            
            # Show loading indicator
            loading_label = tk.Label(
                self.scrollable_results_frame,
                text="Searching...",
                font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
                fg='#0078d7',
                bg='#ffffff'
            )
            loading_label.pack(pady=self.padding['medium'])
            
            # Update the UI immediately
            self.root.update()
            
            # Perform search in background thread
            threading.Thread(
                target=self._perform_music_search, 
                args=(query,),
                daemon=True
            ).start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start search: {e}")

    def _perform_music_search(self, query):
        """Perform the actual music search (run in background thread)"""
        try:
            # Use yt-dlp to search YouTube with more robust settings
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'extract_flat': True,
                'default_search': 'ytsearch10:',
                'noplaylist': True,
                'force_generic_extractor': True,
                'extractor_args': {
                    'youtube': {
                        'skip': ['dash', 'hls']
                    }
                }
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                try:
                    results = ydl.extract_info(f"ytsearch10:{query}", download=False)
                    
                    # Check if we got valid results
                    if not results or 'entries' not in results or not results['entries']:
                        self.root.after(0, lambda: self._show_no_results())
                        return
                    
                    # Filter out invalid entries
                    valid_entries = [e for e in results['entries'] if e and e.get('url')]
                    if not valid_entries:
                        self.root.after(0, lambda: self._show_no_results())
                        return
                    
                    # Process results in main thread
                    self.root.after(0, lambda: self._display_search_results({'entries': valid_entries}))
                    
                except Exception as e:
                    self.root.after(0, lambda: self._show_search_error(f"Search failed: {str(e)}"))
                    print(f"Search error: {str(e)}")
                    
        except Exception as e:
            self.root.after(0, lambda: self._show_search_error(f"Search initialization failed: {str(e)}"))
            print(f"Search init error: {str(e)}")

    def _show_no_results(self):
        """Show no results message"""
        for widget in self.scrollable_results_frame.winfo_children():
            widget.destroy()
        
        tk.Label(
            self.scrollable_results_frame,
            text="No results found. Try a different search term.",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=self.padding['medium'])

    def _show_search_error(self, message):
        """Show search error message"""
        for widget in self.scrollable_results_frame.winfo_children():
            widget.destroy()
        
        tk.Label(
            self.scrollable_results_frame,
            text=f"Error: {message}",
            font=font.Font(family="Segoe UI", size=self.font_sizes['small']),
            fg='#FF3B30',
            bg='#ffffff'
        ).pack(pady=self.padding['medium'])

    def _display_search_results(self, results):
        """Display search results in the UI"""
        # Clear loading indicator
        for widget in self.scrollable_results_frame.winfo_children():
            widget.destroy()
        
        if not results or 'entries' not in results or not results['entries']:
            self._show_no_results()
            return
        
        # Create a scrollable frame if it doesn't exist
        if not hasattr(self, 'results_canvas'):
            self._create_results_scrollable_area()
        
        for entry in results['entries']:
            if not entry or not entry.get('url'):
                continue
                
            # Create result frame for each track
            result_frame = tk.Frame(self.scrollable_results_frame, bg='#ffffff')
            result_frame.pack(fill=tk.X, pady=self.padding['tiny'], padx=self.padding['small'])
            
            # Track title (truncate if too long)
            title = entry.get('title', 'Unknown Track')[:50]
            if len(entry.get('title', '')) > 50:
                title += "..."
                
            # Artist info if available
            artist = entry.get('uploader', 'Unknown Artist')[:30]
            
            # Title and artist label
            info_frame = tk.Frame(result_frame, bg='#ffffff')
            info_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            tk.Label(
                info_frame,
                text=title,
                font=font.Font(family="Segoe UI", size=self.font_sizes['small'], weight='bold'),
                fg='#0078d7',
                bg='#ffffff',
                anchor='w'
            ).pack(fill=tk.X)
            
            tk.Label(
                info_frame,
                text=artist,
                font=font.Font(family="Segoe UI", size=self.font_sizes['tiny']),
                fg='#0078d7',
                bg='#ffffff',
                anchor='w'
            ).pack(fill=tk.X)
            
            # Play button (Frutiger Aero green)
            play_btn = tk.Label(
                result_frame,
                text="▶️",
                font=font.Font(size=self.font_sizes['small']),
                bg='#34C759',
                fg='white',
                bd=0,
                padx=self.padding['small'],
                pady=self.padding['tiny'],
                relief=tk.RAISED
            )
            play_btn.pack(side=tk.RIGHT, padx=self.padding['small'])
            play_btn.bind("<Button-1>", lambda e, url=entry['url'], title=title, artist=artist: 
                        self.play_song(url, title, artist))
            
            # Button effects
            play_btn.bind("<Enter>", lambda e, b=play_btn: b.config(bg='#30D158'))
            play_btn.bind("<Leave>", lambda e, b=play_btn: b.config(bg='#34C759'))

    def _create_results_scrollable_area(self):
        """Create scrollable area for search results"""
        self.results_canvas = tk.Canvas(self.search_results_frame, bg='#ffffff', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.search_results_frame, orient="vertical", command=self.results_canvas.yview)
        self.scrollable_results_frame = tk.Frame(self.results_canvas, bg='#ffffff')
        
        self.scrollable_results_frame.bind(
            "<Configure>",
            lambda e: self.results_canvas.configure(
                scrollregion=self.results_canvas.bbox("all")
            )
        )
        
        self.results_canvas.create_window((0, 0), window=self.scrollable_results_frame, anchor="nw")
        self.results_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.results_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def play_song(self, url, title, artist="Unknown Artist"):
        """Play a song from YouTube URL"""
        try:
            # Stop any currently playing music
            self.player.stop()
            
            # Configure yt-dlp options for better compatibility
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'no_warnings': True,
                'ignoreerrors': True,
                'extract_flat': True,
                'force_generic_extractor': True,
                'noplaylist': True,
                'extractor_args': {
                    'youtube': {
                        'skip': ['dash', 'hls']
                    }
                }
            }
            
            # Extract the best audio URL
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise Exception("Could not extract video info")
                
                # Get the best audio format URL with proper error handling
                formats = info.get('formats', [])
                if not formats:
                    raise Exception("No formats available for this video")
                    
                # Filter audio formats and handle None values
                audio_formats = []
                for f in formats:
                    if f.get('acodec') != 'none':
                        # Ensure we have both URL and bitrate info
                        if f.get('url') and f.get('abr', 0) is not None:
                            audio_formats.append(f)
                
                if not audio_formats:
                    raise Exception("No valid audio formats found")
                    
                # Safely get format with highest bitrate
                best_audio = max(audio_formats, key=lambda f: float(f.get('abr', 0)))
                audio_url = best_audio['url']
            
            # Set media with the direct audio URL
            media = self.vlc_instance.media_new(audio_url)
            media.add_option('network-caching=3000')  # Increase network cache
            media.add_option('http-reconnect=true')   # Enable reconnection
            self.player.set_media(media)
            
            # Play
            self.player.play()
            
            # Update UI
            self.current_song_url = url
            self.current_song_title = title
            self.current_song_artist = artist
            
            self.song_title_label.config(text=self.current_song_title)
            self.song_artist_label.config(text=self.current_song_artist)
            self.play_pause_btn.config(text="⏸")
            
            # Try to get thumbnail
            threading.Thread(target=self._get_song_thumbnail, daemon=True).start()
            
            # Start progress updater
            self.update_song_progress()
            
        except Exception as e:
            error_msg = str(e)
            if "'>' not supported between instances of 'NoneType' and 'float'" in error_msg:
                error_msg = "Failed to process audio formats. Please try another song."
            messagebox.showerror("Error", f"Failed to play song: {error_msg}")
            print(f"Playback error: {error_msg}")

    def _get_song_thumbnail(self):
        """Try to get thumbnail for current song (run in background)"""
        try:
            if not self.current_song_url:
                return
                
            # Use yt-dlp to get thumbnail
            ydl_opts = {
                'quiet': True,
                'extract_flat': True
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.current_song_url, download=False)
                thumbnail_url = info.get('thumbnail', '')
                
                if thumbnail_url:
                    # Download and resize thumbnail
                    with urllib.request.urlopen(thumbnail_url) as url:
                        img_data = url.read()
                    
                    img = Image.open(BytesIO(img_data))
                    img = img.resize((int(200 * self.scale_factor), int(200 * self.scale_factor)), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    
                    # Update in main thread
                    self.root.after(0, lambda: self._set_album_art(photo))
                    
        except Exception:
            pass  # Silently fail if thumbnail can't be loaded

    def _set_album_art(self, photo):
        """Set album art in UI (called from main thread)"""
        self.current_song_thumbnail = photo  # Keep reference
        self.album_art_label.config(image=photo)

    def toggle_play_pause(self):
        """Toggle between play and pause"""
        if self.player.is_playing():
            self.player.pause()
            self.play_pause_btn.config(text="▶️")
        else:
            if self.current_song_url:
                self.player.play()
                self.play_pause_btn.config(text="⏸")
            else:
                messagebox.showinfo("Info", "No song selected")

    def prev_song(self):
        """Play previous song in queue (not implemented yet)"""
        messagebox.showinfo("Info", "Previous song functionality not implemented yet")

    def next_song(self):
        """Play next song in queue (not implemented yet)"""
        messagebox.showinfo("Info", "Next song functionality not implemented yet")

    def update_song_progress(self):
        """Update the song progress bar and time display"""
        if not self.player.is_playing():
            # Check if there was an error
            if self.player.get_state() == vlc.State.Error:
                self.root.after(0, lambda: messagebox.showerror(
                    "Playback Error", 
                    "Failed to play the song. YouTube may have blocked the stream."
                ))
                return
                
            return
            
        try:
            # Get song length and current position
            length_ms = self.player.get_length()
            pos_ms = self.player.get_time()
            
            if length_ms > 0 and pos_ms >= 0:
                # Update progress bar
                progress = (pos_ms / length_ms) * 100
                self.progress_bar['value'] = progress
                
                # Update time labels
                self.current_time_label.config(text=self._format_time(pos_ms))
                self.total_time_label.config(text=self._format_time(length_ms))
            
            # Schedule next update
            self.root.after(1000, self.update_song_progress)
        except Exception as e:
            print(f"Progress update error: {str(e)}")
            # Try to continue updating
            self.root.after(1000, self.update_song_progress)

    def _format_time(self, ms):
        """Format milliseconds to MM:SS"""
        seconds = int(ms / 1000)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"

    def bind_activity_events(self):
        """Bind events to track user activity for screen timeout"""
        events = [
            "<Button-1>", "<ButtonRelease-1>", 
            "<KeyPress>", "<KeyRelease>",
            "<Motion>"
        ]
        
        for event in events:
            self.root.bind(event, self._record_activity)

    def _record_activity(self, event):
        """Record user activity for screen timeout"""
        self.last_activity = time.time()

    def check_inactivity(self):
        """Check for inactivity and lock screen if timeout reached"""
        if self.current_screen == "lock":
            self.root.after(1000, self.check_inactivity)
            return
            
        if time.time() - self.last_activity > self.inactivity_timeout:
            self.show_lock_screen()
        
        self.root.after(1000, self.check_inactivity)

    def start_background_tasks(self):
        """Start background tasks for alarm checking and inactivity timeout"""
        # Alarm checker
        threading.Thread(target=self._alarm_checker, daemon=True).start()
        
        # Inactivity checker
        self.check_inactivity()

    def _alarm_checker(self):
        """Background thread to check for alarms"""
        while True:
            try:
                self.check_alarms()
            except Exception as e:
                print(f"Error in alarm checker: {e}")
            time.sleep(30)  # Check every 30 seconds

    def run(self):
        """Run the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = AlarmClockApp()
    app.run()
