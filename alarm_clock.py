#!/usr/bin/env python3
"""
Raspberry Pi Touch Screen Alarm Clock with Apple Music and Tuya Smart Bulb Integration
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
from tkinterweb import HtmlFrame  # For Apple Music iframe
from tuya_connector import TuyaOpenAPI
from PIL import Image, ImageTk
import math

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
            "alarm_volume": 1.0  # Max volume
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
        """Create lock screen with full-screen fish tank background"""
        self.lock_frame = tk.Frame(self.main_frame, bg='black')
        self.lock_frame.pack(fill=tk.BOTH, expand=True)
        
        # Fish tank canvas - full screen
        self.fish_tank = tk.Canvas(self.lock_frame, bg='#006994', highlightthickness=0)
        self.fish_tank.pack(fill=tk.BOTH, expand=True)
        
        # Draw fish tank elements after canvas is sized
        self.fish_tank.bind("<Configure>", lambda event: self.draw_fish_tank())
        
        # Create a transparent overlay for time/date/unlock button
        overlay_frame = tk.Frame(self.fish_tank, bg='', bd=0)
        overlay_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # Time display - make background transparent
        self.time_font = font.Font(family="Segoe UI Light", size=96, weight="normal")
        self.time_label = tk.Label(
            overlay_frame,
            text="",
            font=self.time_font,
            fg='white',
            bg='#006994',  # Use a valid color for background
            bd=0
        )
        self.time_label.pack(pady=20)
        
        # Date display - transparent background
        self.date_font = font.Font(family="Segoe UI", size=24, weight="normal")
        self.date_label = tk.Label(
            overlay_frame,
            text="",
            font=self.date_font,
            fg='white',
            bg='#006994',  # Use a valid color for background
            bd=0
        )
        self.date_label.pack(pady=10)
        
        # Tap to unlock button
        unlock_btn = tk.Label(
            overlay_frame,
            text="Tap to unlock",
            font=font.Font(family="Segoe UI", size=16),
            fg='white',
            bg='#34C759',
            bd=0,
            padx=20,
            pady=8,
            relief=tk.RAISED
        )
        unlock_btn.pack(pady=40)
        
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
        for _ in range(30):
            x = random.randint(50, width-50)  # Random x across width
            y = random.randint(height//2, height-bottom_height)  # Start in middle to bottom
            size = random.randint(5, 20)
            speed = 1 + random.random() * 3
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
        for _ in range(10):
            x = random.randint(100, width-100)
            y = random.randint(100, height-bottom_height-100)
            size = random.randint(30, 70)
            color = random.choice(colors)
            speed = 1 + random.random() * 3
            direction = 1 if random.random() > 0.5 else -1
            fish_parts = self.draw_fish(x, y, size, color, direction)
            self.fishes.append({
                'x': x, 'y': y, 'size': size, 
                'color': color, 'speed': speed, 
                'direction': direction,
                'parts': fish_parts
            })

    def animate_fish(self):
        """Animate fish and bubbles"""
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
        
        # Lock button (Frutiger Aero green)
        lock_btn = tk.Label(
            header_frame,
            text="🔒",
            font=font.Font(size=24),
            bg='#34C759',
            fg='white',
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
        
        # Add alarm button (Frutiger Aero green)
        add_alarm_btn = tk.Label(
            alarm_widget,
            text="+ Add Alarm",
            font=font.Font(family="Segoe UI", size=14),
            bg='#34C759',
            fg='white',
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
        
        # Music button (Frutiger Aero green)
        music_btn = tk.Label(
            music_widget,
            text="Open Apple Music",
            font=font.Font(family="Segoe UI", size=14),
            bg='#34C759',
            fg='white',
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
        
        # Light control buttons (Frutiger Aero green)
        btn_frame = tk.Frame(lights_widget, bg='#ffffff')
        btn_frame.pack(pady=10)
        
        on_btn = tk.Label(
            btn_frame,
            text="ON",
            font=font.Font(family="Segoe UI", size=14, weight="bold"),
            bg='#34C759',
            fg='white',
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
            bg='#34C759',
            fg='white',
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
        
        # Settings button (Frutiger Aero green)
        settings_btn = tk.Label(
            settings_widget,
            text="Configure",
            font=font.Font(family="Segoe UI", size=14),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=20,
            pady=8,
            relief=tk.RAISED
        )
        settings_btn.pack(pady=20)
        settings_btn.bind("<Button-1>", lambda e: self.show_settings_screen())
    
    def create_alarm_setup_screen(self):
        """Create alarm setup screen with radial time picker"""
        self.alarm_setup_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
        
        # Header with glass effect
        header = tk.Frame(self.alarm_setup_frame, bg='#34C759', height=60)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # Back button (Frutiger Aero style)
        back_btn = tk.Label(
            header,
            text="← Back",
            font=font.Font(family="Segoe UI", size=18),
            bg='#34C759',
            fg='white',
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
            fg='white',
            bg='#34C759'
        ).pack(anchor='center')
        
        # Alarm setup form with glass panel
        form_frame = tk.Frame(self.alarm_setup_frame, bg='#ffffff', relief=tk.FLAT, bd=0)
        form_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20, ipadx=10, ipady=10)
        form_frame.config(highlightbackground='#a0c0e0', highlightthickness=1)
        
        # Radial time picker
        time_frame = tk.Frame(form_frame, bg='#ffffff', relief=tk.FLAT, bd=0)
        time_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(
            time_frame,
            text="Time",
            font=font.Font(family="Segoe UI", size=18, weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        ).pack(pady=10)
        
        # Create radial time picker
        self.create_radial_time_picker(time_frame)
        
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
        
        # Save button (Frutiger Aero green)
        save_btn = tk.Label(
            form_frame,
            text="Save Alarm",
            font=font.Font(family="Segoe UI", size=18, weight="bold"),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=40,
            pady=15,
            relief=tk.RAISED
        )
        save_btn.pack(pady=30)
        save_btn.bind("<Button-1>", lambda e: self.save_alarm())
    
    def create_radial_time_picker(self, parent):
        """Create Apple-style radial time picker with Frutiger Aero enhancements"""
        self.radial_frame = tk.Frame(parent, bg='#ffffff')
        self.radial_frame.pack(pady=10)
        
        # Create canvas for radial dial with larger size
        self.radial_canvas = tk.Canvas(
            self.radial_frame, 
            width=320, 
            height=320, 
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
        time_display_frame.pack(pady=10)
        
        self.time_display_var = tk.StringVar(value="12:00 AM")
        self.time_display = tk.Label(
            time_display_frame,
            textvariable=self.time_display_var,
            font=font.Font(family="Segoe UI", size=32, weight="bold"),
            fg='#0078d7',
            bg='#ffffff'
        )
        self.time_display.pack(side=tk.LEFT)
        
        # AM/PM toggle button (Frutiger Aero style)
        am_pm_btn = tk.Label(
            time_display_frame,
            textvariable=self.am_pm_var,
            font=font.Font(family="Segoe UI", size=16),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=10,
            pady=5,
            relief=tk.RAISED
        )
        am_pm_btn.pack(side=tk.LEFT, padx=10)
        am_pm_btn.bind("<Button-1>", lambda e: self.toggle_am_pm())
        
        # Draw radial dial
        self.draw_radial_dial()
        
        # Digital time input as fallback
        digital_frame = tk.Frame(self.radial_frame, bg='#ffffff')
        digital_frame.pack(pady=10)
        
        tk.Label(digital_frame, text="or enter time:", font=font.Font(family="Segoe UI", size=12), 
                fg='#0078d7', bg='#ffffff').pack()
        
        time_entry_frame = tk.Frame(digital_frame, bg='#ffffff')
        time_entry_frame.pack()
        
        # Hour entry
        self.hour_entry = ttk.Spinbox(
            time_entry_frame,
            from_=1, to=12,
            width=2,
            font=font.Font(family="Segoe UI", size=16),
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
            font=font.Font(family="Segoe UI", size=16),
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
        center_x, center_y = 160, 160
        radius = 140
        
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
                x-20, y-20, x+20, y+20,
                outline='#e0f0ff', fill='#e0f0ff'
            )
            
            self.radial_canvas.create_text(
                x, y,
                text=str(hour),
                font=font.Font(family="Segoe UI", size=18, weight="bold"),
                fill='#0078d7'
            )
        
        # Draw minute markers with smaller decorative elements
        for minute in range(0, 60, 5):
            if minute % 15 == 0:  # Skip where hours are
                continue
            angle = math.radians((minute * 6) - 90)
            x = center_x + (radius * 0.85) * math.cos(angle)
            y = center_y + (radius * 0.85) * math.sin(angle)
            
            self.radial_canvas.create_oval(
                x-8, y-8, x+8, y+8,
                outline='#e0f0ff', fill='#e0f0ff'
            )
            
            self.radial_canvas.create_text(
                x, y,
                text=str(minute).zfill(2),
                font=font.Font(family="Segoe UI", size=12),
                fill='#0078d7'
            )
        
        # Draw clock hand
        hour = int(self.hour_var.get())
        minute = int(self.minute_var.get())
        
        # Hour hand
        hour_angle = math.radians(((hour % 12) * 30 + minute * 0.5) - 90)
        hour_length = radius * 0.5
        self.radial_canvas.create_line(
            center_x, center_y,
            center_x + hour_length * math.cos(hour_angle),
            center_y + hour_length * math.sin(hour_angle),
            fill='#0078d7', width=4, capstyle=tk.ROUND
        )
        
        # Minute hand
        minute_angle = math.radians((minute * 6) - 90)
        minute_length = radius * 0.7
        self.radial_canvas.create_line(
            center_x, center_y,
            center_x + minute_length * math.cos(minute_angle),
            center_y + minute_length * math.sin(minute_angle),
            fill='#34C759', width=3, capstyle=tk.ROUND
        )
        
        # Center dot
        self.radial_canvas.create_oval(
            center_x-8, center_y-8, center_x+8, center_y+8,
            fill='#0078d7', outline=''
        )

    def on_radial_drag(self, event):
        """Handle dragging on radial dial"""
        self.update_radial_time(event.x, event.y)

    def on_radial_click(self, event):
        """Handle click on radial dial"""
        self.update_radial_time(event.x, event.y)

    def update_radial_time(self, x, y):
        """Update time based on radial dial position"""
        center_x, center_y = 160, 160
        dx = x - center_x
        dy = y - center_y
        
        # Calculate angle (0-360 degrees)
        angle = math.degrees(math.atan2(dy, dx)) + 90
        if angle < 0:
            angle += 360
        
        # Determine if selecting hour or minute
        radius = math.sqrt(dx*dx + dy*dy)
        if radius < 100:  # Inner circle - hours
            hour = round(angle / 30) % 12
            if hour == 0:
                hour = 12
            self.hour_var.set(str(hour))
            self.hour_entry.delete(0, tk.END)
            self.hour_entry.insert(0, str(hour))
        else:  # Outer circle - minutes
            minute = round(angle / 6) % 60
            self.minute_var.set(str(minute).zfill(2))
            self.minute_entry.delete(0, tk.END)
            self.minute_entry.insert(0, str(minute).zfill(2))
        
        # Update display and redraw dial
        self.update_time_display()
        self.draw_radial_dial()

    def update_time_display(self):
        """Update the time display label"""
        time_str = f"{self.hour_var.get()}:{self.minute_var.get().zfill(2)} {self.am_pm_var.get()}"
        self.time_display_var.set(time_str)

    def create_settings_screen(self):
        """Create settings screen in Frutiger Aero style"""
        self.settings_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
        
        # Header with glass effect
        header = tk.Frame(self.settings_frame, bg='#34C759', height=60)
        header.pack(fill=tk.X, padx=0, pady=0)
        header.pack_propagate(False)
        
        # Back button (Frutiger Aero style)
        back_btn = tk.Label(
            header,
            text="← Back",
            font=font.Font(family="Segoe UI", size=18),
            bg='#34C759',
            fg='white',
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
            fg='white',
            bg='#34C759'
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
        
        # Alarm volume slider
        tk.Label(form_frame, text="Alarm Volume:", fg='#0078d7', bg='#ffffff', font=font.Font(family="Segoe UI", size=12)).pack(anchor='w')
        self.volume_slider = tk.Scale(
            form_frame,
            from_=0, to=100,
            orient=tk.HORIZONTAL,
            bg='#ffffff',
            fg='#0078d7',
            highlightbackground='#a0c0e0',
            troughcolor='#e0f0ff'
        )
        self.volume_slider.set(self.config.get("alarm_volume", 1.0) * 100)
        self.volume_slider.pack(fill=tk.X, pady=(0, 20))
        
        # Save button (Frutiger Aero green)
        save_settings_btn = tk.Label(
            form_frame,
            text="Save Settings",
            font=font.Font(family="Segoe UI", size=16, weight="bold"),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=30,
            pady=10,
            relief=tk.RAISED
        )
        save_settings_btn.pack(pady=20)
        save_settings_btn.bind("<Button-1>", lambda e: self.save_settings())
    
    def create_music_screen(self):
        """Create music screen with Apple Music iframe"""
        if not hasattr(self, 'music_frame') or self.music_frame is None:
            self.music_frame = tk.Frame(self.main_frame, bg='#e0f0ff')
            
            # Header with glass effect
            header = tk.Frame(self.music_frame, bg='#34C759', height=60)
            header.pack(fill=tk.X, padx=0, pady=0)
            header.pack_propagate(False)
            
            # Back button (Frutiger Aero style)
            back_btn = tk.Label(
                header,
                text="← Back",
                font=font.Font(family="Segoe UI", size=18),
                bg='#34C759',
                fg='white',
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
                fg='white',
                bg='#34C759'
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
                    bg='#34C759',
                    fg='white',
                    bd=0,
                    padx=40,
                    pady=20,
                    relief=tk.RAISED
                )
                web_btn.pack(pady=20)
                web_btn.bind("<Button-1>", lambda e: webbrowser.open("https://music.apple.com"))
    
    def show_lock_screen(self):
        """Show the lock screen"""
        self.current_screen = "lock"
        self.lock_frame.pack(fill=tk.BOTH, expand=True)
        self.main_screen_frame.pack_forget()
        self.alarm_setup_frame.pack_forget()
        self.settings_frame.pack_forget()
        if hasattr(self, 'music_frame'):
            self.music_frame.pack_forget()
        
        # Reset inactivity timer
        self.last_activity = time.time()
    
    def show_main_screen(self):
        """Show the main screen"""
        self.current_screen = "main"
        self.lock_frame.pack_forget()
        self.main_screen_frame.pack(fill=tk.BOTH, expand=True)
        self.alarm_setup_frame.pack_forget()
        self.settings_frame.pack_forget()
        if hasattr(self, 'music_frame'):
            self.music_frame.pack_forget()
        
        # Update alarm list
        self.update_alarm_list()
        
        # Reset inactivity timer
        self.last_activity = time.time()
    
    def show_alarm_setup(self):
        """Show the alarm setup screen"""
        self.current_screen = "alarm_setup"
        self.lock_frame.pack_forget()
        self.main_screen_frame.pack_forget()
        self.alarm_setup_frame.pack(fill=tk.BOTH, expand=True)
        self.settings_frame.pack_forget()
        if hasattr(self, 'music_frame'):
            self.music_frame.pack_forget()
        
        # Reset form
        self.hour_var.set("12")
        self.minute_var.set("00")
        self.time_display.config(text="12:00")
        self.repeat_var.set(True)
        self.light_control_var.set(False)
        
        # Reset inactivity timer
        self.last_activity = time.time()
    
    def show_settings_screen(self):
        """Show the settings screen"""
        self.current_screen = "settings"
        self.lock_frame.pack_forget()
        self.main_screen_frame.pack_forget()
        self.alarm_setup_frame.pack_forget()
        self.settings_frame.pack(fill=tk.BOTH, expand=True)
        if hasattr(self, 'music_frame'):
            self.music_frame.pack_forget()
        
        # Reset inactivity timer
        self.last_activity = time.time()
    
    def show_music_screen(self):
        """Show the music screen"""
        self.current_screen = "music"
        self.lock_frame.pack_forget()
        self.main_screen_frame.pack_forget()
        self.alarm_setup_frame.pack_forget()
        self.settings_frame.pack_forget()
        self.music_frame.pack(fill=tk.BOTH, expand=True)
        
        # Reset inactivity timer
        self.last_activity = time.time()
    
    def unlock_screen(self, event=None):
        """Unlock the screen and show main screen"""
        self.show_main_screen()
    
    def load_alarms(self):
        """Load saved alarms from config"""
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
    
    def update_alarm_list(self):
        """Update the alarm list display"""
        # Clear existing alarms
        for widget in self.alarm_list_frame.winfo_children():
            widget.destroy()
        
        if not self.alarms:
            tk.Label(
                self.alarm_list_frame,
                text="No alarms set",
                font=font.Font(family="Segoe UI", size=14),
                fg='#888888',
                bg='#ffffff'
            ).pack(pady=20)
            return
        
        # Sort alarms by time
        sorted_alarms = sorted(self.alarms, key=lambda x: (x['hour'], x['minute']))
        
        for alarm in sorted_alarms:
            alarm_frame = tk.Frame(self.alarm_list_frame, bg='#ffffff')
            alarm_frame.pack(fill=tk.X, pady=5)
            
            # Time label
            time_str = f"{alarm['hour']:02d}:{alarm['minute']:02d}"
            tk.Label(
                alarm_frame,
                text=time_str,
                font=font.Font(family="Segoe UI", size=24),
                fg='#0078d7',
                bg='#ffffff'
            ).pack(side=tk.LEFT, padx=10)
            
            # Repeat indicator
            repeat_text = "Daily" if alarm['repeat'] else "Once"
            tk.Label(
                alarm_frame,
                text=repeat_text,
                font=font.Font(family="Segoe UI", size=14),
                fg='#888888',
                bg='#ffffff'
            ).pack(side=tk.LEFT, padx=10)
            
            # Light control indicator
            if alarm['light_control']:
                tk.Label(
                    alarm_frame,
                text="💡",
                font=font.Font(size=14),
                fg='#FFD700',
                bg='#ffffff'
            ).pack(side=tk.LEFT, padx=5)
            
            # Delete button (Frutiger Aero red)
            delete_btn = tk.Label(
                alarm_frame,
                text="✕",
                font=font.Font(size=16),
                fg='white',
                bg='#FF3B30',
                bd=0,
                padx=8,
                pady=2,
                relief=tk.RAISED
            )
            delete_btn.pack(side=tk.RIGHT, padx=5)
            delete_btn.bind("<Button-1>", lambda e, a=alarm: self.delete_alarm(a))
    
    def save_alarm(self):
        """Save the new alarm"""
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            am_pm = self.am_pm_var.get()
            repeat = self.repeat_var.get()
            light_control = self.light_control_var.get()

            # Convert to 24-hour format
            if am_pm == "AM":
                if hour == 12:
                    hour_24 = 0
                else:
                    hour_24 = hour
            else:  # PM
                if hour == 12:
                    hour_24 = 12
                else:
                    hour_24 = hour + 12

            if hour_24 < 0 or hour_24 > 23 or minute < 0 or minute > 59:
                messagebox.showerror("Invalid Time", "Please enter a valid time (12-hour format with AM/PM)")
                return

            new_alarm = {
                'hour': hour_24,
                'minute': minute,
                'repeat': repeat,
                'light_control': light_control,
                'enabled': True
            }

            self.alarms.append(new_alarm)
            self.save_alarms()
            self.show_main_screen()
        except ValueError:
            messagebox.showerror("Invalid Time", "Please enter a valid time (12-hour format with AM/PM)")

    def delete_alarm(self, alarm):
        """Delete an alarm"""
        self.alarms.remove(alarm)
        self.save_alarms()
        self.update_alarm_list()
    
    def save_settings(self):
        """Save settings from the settings screen"""
        self.config['tuya_access_id'] = self.access_id_entry.get()
        self.config['tuya_access_secret'] = self.access_secret_entry.get()
        self.config['tuya_device_id'] = self.device_id_entry.get()
        self.config['alarm_volume'] = self.volume_slider.get() / 100.0
        
        self.save_config()
        self.init_tuya()  # Reinitialize Tuya connection
        
        messagebox.showinfo("Settings Saved", "Settings have been saved successfully")
        self.show_main_screen()
    
    def control_light(self, on):
        """Control the Tuya smart bulb"""
        if not self.tuya_api:
            messagebox.showerror("Error", "Tuya API not configured")
            return
        
        try:
            commands = {
                "commands": [{
                    "code": "switch_led",
                    "value": on
                }]
            }
            response = self.tuya_api.post(
                f"/v1.0/iot-03/devices/{self.config['tuya_device_id']}/commands",
                commands
            )
            
            if not response.get('success', False):
                messagebox.showerror("Error", "Failed to control light")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to control light: {str(e)}")
    
    def check_alarms(self):
        """Check if any alarms should trigger"""
        now = datetime.datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        
        for alarm in self.alarms:
            if not alarm['enabled']:
                continue
                
            if (alarm['hour'] == current_hour and 
                alarm['minute'] == current_minute and
                (alarm['repeat'] or not alarm.get('triggered_today', False))):
                
                # Mark alarm as triggered
                alarm['triggered_today'] = True
                self.save_alarms()
                
                # Set as active alarm
                self.active_alarm = alarm
                
                # Trigger alarm
                self.trigger_alarm()
                
                # Control lights if enabled
                if alarm['light_control'] and self.tuya_api:
                    self.control_light(True)
    
    def trigger_alarm(self):
        """Trigger the alarm sound and notification"""
        # Show alarm screen
        self.show_alarm_notification()
        
        # Play alarm sound
        try:
            pygame.mixer.music.load("alarm_sound.mp3")
            pygame.mixer.music.set_volume(self.config['alarm_volume'])
            pygame.mixer.music.play(-1)  # Loop indefinitely
        except:
            # Fallback beep sound
            self.root.bell()
    
    def show_alarm_notification(self):
        """Show alarm notification overlay"""
        self.alarm_overlay = tk.Toplevel(self.root)
        self.alarm_overlay.attributes('-fullscreen', True)
        self.alarm_overlay.attributes('-topmost', True)
        self.alarm_overlay.configure(bg='#0078d7')
        
        # Time display
        time_font = font.Font(family="Segoe UI Light", size=96, weight="bold")
        time_label = tk.Label(
            self.alarm_overlay,
            text=f"{self.active_alarm['hour']:02d}:{self.active_alarm['minute']:02d}",
            font=time_font,
            fg='white',
            bg='#0078d7'
        )
        time_label.pack(pady=50)
        
        # Alarm message
        msg_font = font.Font(family="Segoe UI", size=24)
        msg_label = tk.Label(
            self.alarm_overlay,
            text="Time to wake up!",
            font=msg_font,
            fg='white',
            bg='#0078d7'
        )
        msg_label.pack(pady=20)
        
        # Control buttons
        btn_frame = tk.Frame(self.alarm_overlay, bg='#0078d7')
        btn_frame.pack(pady=50)
        
        # Snooze button (Frutiger Aero green)
        snooze_btn = tk.Label(
            btn_frame,
            text=f"Snooze ({self.snooze_time} min)",
            font=font.Font(family="Segoe UI", size=18),
            bg='#34C759',
            fg='white',
            bd=0,
            padx=30,
            pady=15,
            relief=tk.RAISED
        )
        snooze_btn.pack(side=tk.LEFT, padx=20)
        snooze_btn.bind("<Button-1>", lambda e: self.snooze_alarm())
        
        # Dismiss button (Frutiger Aero red)
        dismiss_btn = tk.Label(
            btn_frame,
            text="Dismiss",
            font=font.Font(family="Segoe UI", size=18),
            bg='#FF3B30',
            fg='white',
            bd=0,
            padx=30,
            pady=15,
            relief=tk.RAISED
        )
        dismiss_btn.pack(side=tk.LEFT, padx=20)
        dismiss_btn.bind("<Button-1>", lambda e: self.dismiss_alarm())
    
    def snooze_alarm(self):
        """Snooze the current alarm"""
        pygame.mixer.music.stop()
        self.alarm_overlay.destroy()
        
        # Calculate snooze time
        snooze_time = datetime.datetime.now() + datetime.timedelta(minutes=self.snooze_time)
        self.active_alarm['hour'] = snooze_time.hour
        self.active_alarm['minute'] = snooze_time.minute
        self.active_alarm['repeat'] = False
        self.active_alarm['enabled'] = True
        self.active_alarm['triggered_today'] = False
        
        self.save_alarms()
        self.update_alarm_list()
        self.active_alarm = None
    
    def dismiss_alarm(self):
        """Dismiss the current alarm"""
        pygame.mixer.music.stop()
        self.alarm_overlay.destroy()
        
        if not self.active_alarm['repeat']:
            self.active_alarm['enabled'] = False
            self.save_alarms()
            self.update_alarm_list()
        
        self.active_alarm = None
    
    def update_time(self):
        """Update the time display"""
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%A, %B %d")
        
        if self.current_screen == "lock":
            self.time_label.config(text=time_str)
            self.date_label.config(text=date_str)
        elif self.current_screen == "main":
            self.main_time_label.config(text=time_str)
        
        # Check for alarms every minute
        if now.second == 0:
            self.check_alarms()
        
        # Reset triggered_today flag at midnight
        if now.hour == 0 and now.minute == 0:
            for alarm in self.alarms:
                if 'triggered_today' in alarm:
                    del alarm['triggered_today']
            self.save_alarms()
        
        self.root.after(1000, self.update_time)
    
    def check_inactivity(self):
        """Check for inactivity and return to lock screen"""
        if (self.current_screen != "lock" and 
            time.time() - self.last_activity > self.inactivity_timeout):
            self.show_lock_screen()
        
        self.root.after(1000, self.check_inactivity)
    
    def bind_activity_events(self):
        """Bind events that should reset the inactivity timer"""
        for widget in [self.root, self.main_frame, self.lock_frame, 
                      self.main_screen_frame, self.alarm_setup_frame,
                      self.settings_frame]:
            widget.bind("<Button-1>", self.reset_inactivity_timer)
            widget.bind("<Motion>", self.reset_inactivity_timer)
    
    def reset_inactivity_timer(self, event=None):
        """Reset the inactivity timer"""
        self.last_activity = time.time()
    
    def start_background_tasks(self):
        """Start background update tasks"""
        self.update_time()
        self.check_inactivity()
    
    def run(self):
        """Run the application"""
        self.root.mainloop()

if __name__ == "__main__":
    import random  # For fish tank animation
    
    app = AlarmClockApp()
    app.run()
