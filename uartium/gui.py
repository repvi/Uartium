"""
Uartium - Enterprise UART Monitor
==================================

Professional-grade serial communication monitoring with:
  - Real-time logging and message filtering
  - Performance analytics and metrics
  - Persistent configuration management
  - Robust error handling and recovery
  - Data export and archival
  - Comprehensive status monitoring
"""

from __future__ import annotations

import time
from collections import deque
from typing import Optional
import json
import os
import logging
from datetime import datetime
import threading

import dearpygui.dearpygui as dpg

from uartium.serial_backend import DemoSerialBackend, SerialBackend

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('uartium_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Colour palette  (R, G, B, A  — 0-255)
# ---------------------------------------------------------------------------
LEVEL_COLORS: dict[str, tuple[int, int, int, int]] = {
    "INFO":    (100, 210, 255, 255),   # Electric cyan-blue
    "WARNING": (255, 193, 7, 255),     # Vibrant amber
    "ERROR":   (255, 82, 82, 255),     # Hot red
    "DEBUG":   (189, 147, 249, 255),   # Soft purple
}

# Modern Dark theme - Sleek midnight blue
DARK_THEME = {
    "window_bg": (18, 18, 24, 255),           # Deep midnight
    "child_bg": (24, 24, 32, 255),            # Rich dark blue
    "title_bg": (28, 28, 38, 255),            # Dark blue-grey
    "title_bg_active": (40, 42, 54, 255),     # Slate blue
    "button": (68, 71, 90, 255),              # Modern grey-blue
    "button_hovered": (98, 114, 164, 255),    # Periwinkle blue
    "button_active": (80, 250, 123, 255),     # Bright green
    "header": (44, 47, 62, 255),              # Dark slate
    "header_hovered": (68, 71, 90, 255),      # Light slate
    "text": (248, 248, 242, 255),             # Soft white
    "border": (68, 71, 90, 200),              # Subtle border
    "frame_bg": (30, 30, 40, 255),            # Frame background
    "frame_bg_hovered": (40, 42, 54, 255),    # Hovered frame
    "accent": (139, 233, 253, 255),           # Cyan accent
    "accent_dim": (98, 114, 164, 255),        # Dimmed accent
    "success": (80, 250, 123, 255),           # Success green
    "warning": (255, 193, 7, 255),            # Warning amber
    "error": (255, 82, 82, 255),              # Error red
}

# Modern Light theme - Clean & Bright
LIGHT_THEME = {
    "window_bg": (248, 249, 250, 255),        # Off-white
    "child_bg": (255, 255, 255, 255),         # Pure white
    "title_bg": (233, 236, 239, 255),         # Light grey
    "title_bg_active": (206, 212, 218, 255),  # Medium grey
    "button": (233, 236, 239, 255),           # Light button
    "button_hovered": (13, 110, 253, 255),    # Bright blue
    "button_active": (10, 88, 202, 255),      # Deep blue
    "header": (241, 243, 245, 255),           # Pale grey
    "header_hovered": (222, 226, 230, 255),   # Medium grey
    "text": (33, 37, 41, 255),                # Dark text
    "border": (206, 212, 218, 180),           # Subtle border
    "frame_bg": (248, 249, 250, 255),         # Frame background
    "frame_bg_hovered": (233, 236, 239, 255), # Hovered frame
    "accent": (13, 110, 253, 255),            # Blue accent
    "accent_dim": (108, 117, 125, 255),       # Dimmed accent
    "success": (25, 135, 84, 255),            # Success green
    "warning": (255, 193, 7, 255),            # Warning amber
    "error": (255, 82, 82, 255),              # Error red
}

LEVEL_BADGE: dict[str, str] = {
    "INFO":    "[INFO]  ",
    "WARNING": "[WARN]  ",
    "ERROR":   "[ERROR] ",
    "DEBUG":   "[DEBUG] ",
}

# Numeric ID for the timeline Y-axis (so the chart is categorical-ish)
LEVEL_Y: dict[str, float] = {
    "DEBUG":   1.0,
    "INFO":    2.0,
    "WARNING": 3.0,
    "ERROR":   4.0,
}

# matching scatter colours per level  (normalised 0-1 for plot themes)
LEVEL_PLOT_COLORS: dict[str, tuple[float, float, float, float]] = {
    "INFO":    (0.71, 0.82, 1.00, 1.0),
    "WARNING": (1.00, 0.78, 0.24, 1.0),
    "ERROR":   (1.00, 0.31, 0.31, 1.0),
    "DEBUG":   (0.67, 0.67, 0.67, 1.0),
}

# ---------------------------------------------------------------------------
# App state
# ---------------------------------------------------------------------------
MAX_LOG_LINES = 2000
MAX_TIMELINE_POINTS = 500
SETTINGS_FILE = "uartium_settings.json"


class UartiumApp:
    """Enterprise-grade UART monitoring application."""

    # Common baud rates for serial communication
    BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
    
    # Enterprise configuration constants
    MAX_RECONNECT_ATTEMPTS = 5
    RECONNECT_DELAY = 3.0
    COMMAND_TIMEOUT = 10.0
    BUFFER_RETENTION_DAYS = 7

    def __init__(self, backend=None, initial_baudrate: int = 115200):
        self.backend = backend or DemoSerialBackend(interval=0.5)
        self._initial_baudrate = initial_baudrate
        self._selected_baudrate = initial_baudrate
        self._is_serial_backend = isinstance(backend, SerialBackend)
        self._start_time: Optional[float] = None
        
        # Enterprise features
        self._reconnect_attempts = 0
        self._last_error: Optional[str] = None
        self._session_start_time: Optional[float] = None
        self._error_lock = threading.Lock()
        self._is_running = False

        # per-level timeline data
        self._timeline_x: dict[str, deque] = {lvl: deque(maxlen=MAX_TIMELINE_POINTS) for lvl in LEVEL_Y}
        self._timeline_y: dict[str, deque] = {lvl: deque(maxlen=MAX_TIMELINE_POINTS) for lvl in LEVEL_Y}
        self._timeline_messages: dict[str, deque] = {lvl: deque(maxlen=MAX_TIMELINE_POINTS) for lvl in LEVEL_Y}

        # data monitor state: tracks latest value of each variable
        self._data_vars: dict[str, dict] = {}   # varName -> {"value": ..., "type": ...}
        self._data_table_rows: dict[str, tuple] = {}  # varName -> (name_cell, type_cell, value_cell)

        # dpg tag references (assigned during build)
        self._log_parent: int | str = 0
        self._status_text: int | str = 0
        self._msg_count = 0
        self._plot_series: dict[str, int | str] = {}
        self._x_axis_tag: int | str = 0
        self._baud_input: int | str = 0
        self._timeline_tooltip_window = "timeline_tooltip"
        self._timeline_tooltip_header = "timeline_tooltip_header"
        self._timeline_tooltip_body = "timeline_tooltip_body"
        self._last_hovered_msg_id: int | None = None
        self._timeline_tooltip_pos: tuple[int, int] | None = None
        self._pinned_msg: dict | None = None
        
        # Statistics tracking
        self._level_counts = {"INFO": 0, "WARNING": 0, "ERROR": 0, "DEBUG": 0}
        self._last_stats_update = 0
        self._messages_per_second = 0.0
        self._error_count = 0
        self._dropped_messages = 0
        
        # Timeline filters
        self._level_filters = {"INFO": True, "WARNING": True, "ERROR": True, "DEBUG": True}
        
        # Settings
        self._current_theme = "dark"
        self._stats_visible = True  # Toggle for statistics panel
        self._load_settings()
        
        logger.info(f"Uartium initialized with baudrate={initial_baudrate}")
    
    # -- settings persistence -----------------------------------------------
    def _load_settings(self) -> None:
        """Load settings from JSON file with validation."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                    # Validate theme value
                    theme = settings.get("theme", "dark")
                    if theme not in ("dark", "light"):
                        theme = "dark"
                    self._current_theme = theme
                    self._level_filters = settings.get("level_filters", self._level_filters)
                    self._stats_visible = settings.get("stats_visible", True)
                logger.info(f"Settings loaded from {SETTINGS_FILE}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in settings: {e}")
                self._current_theme = "dark"
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                self._current_theme = "dark"
    
    def _save_settings(self) -> None:
        """Save settings to JSON file with error handling."""
        try:
            settings = {
                "theme": self._current_theme,
                "level_filters": self._level_filters,
                "stats_visible": self._stats_visible,
                "last_saved": datetime.now().isoformat(),
            }
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
            logger.info(f"Settings saved to {SETTINGS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            self._set_error(f"Could not save settings: {e}")
    
    def _apply_theme(self, theme_name: str = None) -> None:
        """Apply a modern color scheme theme to the entire application."""
        if theme_name:
            self._current_theme = theme_name
        
        theme = DARK_THEME if self._current_theme == "dark" else LIGHT_THEME
        
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                # Enhanced rounded corners for modern look
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 8)
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 10)
                dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 10)
                dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 8)
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 6)
                dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 9)
                
                # Improved spacing for better visual hierarchy
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 20, 20)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 14, 10)
                dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 8, 6)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 12, 8)
                dpg.add_theme_style(dpg.mvStyleVar_IndentSpacing, 25)
                dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 14)
                dpg.add_theme_style(dpg.mvStyleVar_GrabMinSize, 12)
                
                # Border thickness for depth
                dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 0)
                dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 0)
                
                # Modern color palette
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, theme["window_bg"])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBg, theme["title_bg"])
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, theme["title_bg_active"])
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, theme["child_bg"])
                dpg.add_theme_color(dpg.mvThemeCol_Button, theme["button"])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, theme["button_hovered"])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, theme["button_active"])
                dpg.add_theme_color(dpg.mvThemeCol_Header, theme["header"])
                dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, theme["header_hovered"])
                dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, theme["button_active"])
                dpg.add_theme_color(dpg.mvThemeCol_Text, theme["text"])
                dpg.add_theme_color(dpg.mvThemeCol_Border, theme["border"])
                dpg.add_theme_color(dpg.mvThemeCol_BorderShadow, (0, 0, 0, 0))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, theme.get("frame_bg", theme["child_bg"]))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, theme.get("frame_bg_hovered", theme["header"]))
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, theme["button_active"])
                dpg.add_theme_color(dpg.mvThemeCol_CheckMark, theme.get("accent", theme["button_hovered"]))
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, theme.get("accent", theme["button_hovered"]))
                dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, theme["button_active"])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, theme["child_bg"])
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, theme.get("accent_dim", theme["button"]))
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, theme.get("accent", theme["button_hovered"]))
                dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive, theme["button_active"])
        dpg.bind_theme(global_theme)

    # -- build UI -----------------------------------------------------------
    def build(self) -> None:
        dpg.create_context()

        # ---- Load and configure font ----
        with dpg.font_registry():
            # Try to load a system font, fallback to default if not available
            try:
                # Increase default font size for better readability
                default_font = dpg.add_font("C:/Windows/Fonts/segoeui.ttf", 16)
                dpg.bind_font(default_font)
            except:
                # Fallback - use default DearPyGui font
                pass

        # ---- global theme ----
        self._apply_theme()

        # ---- settings window (hidden by default) ----
        with dpg.window(label="[SETTINGS] Application Configuration", tag="settings_window", show=False, width=480, height=400, pos=(280, 100), modal=True, no_resize=True):
            dpg.add_spacer(height=8)
            dpg.add_text("[APPEARANCE] Theme Selection", color=(139, 233, 253, 255))
            dpg.add_spacer(height=12)
            
            with dpg.child_window(height=120, border=True):
                dpg.add_spacer(height=6)
                dpg.add_radio_button(
                    ["[DARK] Modern Dark Theme", "[LIGHT] Clean Light Theme"],
                    default_value="[DARK] Modern Dark Theme" if self._current_theme == "dark" else "[LIGHT] Clean Light Theme",
                    callback=self._on_theme_changed,
                    tag="theme_selector"
                )
                dpg.add_spacer(height=6)
            
            dpg.add_spacer(height=20)
            dpg.add_text("[SYSTEM] Status", color=(139, 233, 253, 255))
            dpg.add_spacer(height=8)
            dpg.add_text("Status: Configured | Version: 1.0 Enterprise", color=(180, 200, 210, 255))
            dpg.add_spacer(height=20)
            
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=50)
                dpg.add_button(label="[SAVE] Save Configuration", callback=self._save_settings, width=190, height=35)
                dpg.add_spacer(width=10)
                dpg.add_button(label="[EXIT] Close", callback=lambda: dpg.hide_item("settings_window"), width=130, height=35)

        # ---- main viewport window ----
        with dpg.window(tag="primary_window"):
            # ===== CLEAN TOOLBAR - Arduino IDE Style =====
            with dpg.child_window(height=75, border=False, tag="toolbar_panel"):
                dpg.add_spacer(height=8)
                with dpg.group(horizontal=True):
                    # Main control buttons
                    dpg.add_button(label="START", tag="btn_start", callback=self._on_start, width=100, height=38)
                    dpg.add_button(label="STOP", tag="btn_stop", callback=self._on_stop, enabled=False, width=100, height=38)
                                        
                    # Port configuration group
                    with dpg.group(horizontal=True):
                        dpg.add_text("Port:", color=(200, 200, 210, 255))
                        dpg.add_input_text(default_value="COM3", width=90, tag="port_input")
                        dpg.add_text("Baud:", color=(200, 200, 210, 255))
                        self._baud_input = dpg.add_combo(
                            items=["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"],
                            default_value=str(self._initial_baudrate),
                            width=100,
                            tag="baud_combo",
                            callback=self._on_baud_changed
                        )
                                        
                    # Utility buttons
                    dpg.add_button(label="Statistics", tag="btn_toggle_stats", callback=self._toggle_statistics, width=90, height=28)
                    dpg.add_button(label="Export CSV", callback=self._export_to_csv, tag="btn_export_csv", width=90, height=28)
                    # Status line
                    with dpg.group(horizontal=True):
                        self._status_text = dpg.add_text("Ready", color=(180, 180, 180, 255))
                        self._status_uptime = dpg.add_text("Uptime: 00:00:00", color=(150, 150, 160, 255))

                    dpg.add_spacer(width=20)
                    dpg.add_button(label="Settings", callback=lambda: dpg.show_item("settings_window"), width=80, height=28)
                

            dpg.add_spacer(height=4)

            # ===== COLLAPSIBLE STATISTICS PANEL =====
            with dpg.child_window(height=100, border=True, tag="stats_panel", show=self._stats_visible, no_scrollbar=True):
                dpg.add_spacer(height=6)
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=12)
                    dpg.add_text("STATISTICS", color=(139, 233, 253, 255))
                dpg.add_spacer(height=8)
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=16)
                    with dpg.group():
                        with dpg.group(horizontal=True):
                            self._stat_info = dpg.add_text("INFO: 0", color=LEVEL_COLORS["INFO"])
                            dpg.add_spacer(width=20)
                            self._stat_warn = dpg.add_text("WARN: 0", color=LEVEL_COLORS["WARNING"])
                            dpg.add_spacer(width=20)
                            self._stat_error = dpg.add_text("ERROR: 0", color=LEVEL_COLORS["ERROR"])
                            dpg.add_spacer(width=20)
                            self._stat_debug = dpg.add_text("DEBUG: 0", color=LEVEL_COLORS["DEBUG"])
                        dpg.add_spacer(height=4)
                        self._stat_rate = dpg.add_text("Rate: 0.0 msg/sec | Total: 0 msgs | Errors: 0", color=(189, 147, 249, 255))

            dpg.add_spacer(height=8)

            # ===== MAIN CONTENT AREA - TWO COLUMN LAYOUT =====
            with dpg.group(horizontal=True):
                # LEFT COLUMN: Message log and data monitor
                with dpg.child_window(width=700, border=False):
                    # Message Log
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=8)
                        dpg.add_text("MESSAGE LOG", color=(139, 233, 253, 255))
                    dpg.add_spacer(height=4)
                    self._log_parent = dpg.add_child_window(height=420, border=True, tag="log_window")
                    
                    dpg.add_spacer(height=8)
                    
                    # Data Monitor
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=8)
                        dpg.add_text("DATA MONITOR", color=(139, 233, 253, 255))
                    dpg.add_spacer(height=4)
                    with dpg.child_window(height=220, border=True, tag="data_monitor_window"):
                        with dpg.table(tag="data_table", header_row=True,
                                       borders_innerH=True, borders_innerV=True,
                                       borders_outerH=True, borders_outerV=True,
                                       resizable=True, policy=dpg.mvTable_SizingStretchProp):
                            dpg.add_table_column(label="Variable", width_fixed=True, init_width_or_weight=200)
                            dpg.add_table_column(label="Type", width_fixed=True, init_width_or_weight=80)
                            dpg.add_table_column(label="Value")
                
                dpg.add_spacer(width=8)
                
                # RIGHT COLUMN: Timeline chart
                with dpg.child_window(border=True):
                    dpg.add_spacer(height=6)
                    # Title and filters
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=8)
                        dpg.add_text("EVENT TIMELINE", color=(139, 233, 253, 255))
                    dpg.add_spacer(height=2)
                    # Static filter rows (no scrolling)
                    with dpg.group(horizontal=True):
                        dpg.add_spacer(width=8)
                        dpg.add_text("Show:", color=(180, 180, 190, 255))
                        dpg.add_spacer(width=1)
                        dpg.add_checkbox(
                            label="INFO",
                            default_value=self._level_filters["INFO"],
                            callback=self._on_filter_changed,
                            user_data="INFO",
                            tag=f"filter_INFO"
                        )
                        dpg.add_spacer(width=1)
                        dpg.add_checkbox(
                            label="WARN",
                            default_value=self._level_filters["WARNING"],
                            callback=self._on_filter_changed,
                            user_data="WARNING",
                            tag=f"filter_WARNING"
                        )
                        dpg.add_spacer(width=1)
                        dpg.add_checkbox(
                            label="ERROR",
                            default_value=self._level_filters["ERROR"],
                            callback=self._on_filter_changed,
                            user_data="ERROR",
                            tag=f"filter_ERROR"
                            )
                        dpg.add_spacer(width=1)
                        dpg.add_checkbox(
                            label="DEBUG",
                            default_value=self._level_filters["DEBUG"],
                            callback=self._on_filter_changed,
                            user_data="DEBUG",
                            tag=f"filter_DEBUG"
                        )
                    
                    dpg.add_spacer(height=6)
                    with dpg.plot(label="##timeline", height=-20, width=-20, tag="timeline_plot"):
                        self._x_axis_tag = dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)")
                        with dpg.plot_axis(dpg.mvYAxis, label="Level", tag="timeline_y_axis"):
                            dpg.set_axis_limits("timeline_y_axis", 0.0, 5.0)
                            # one scatter series per level
                            for lvl in LEVEL_Y:
                                col255 = tuple(int(c * 255) for c in LEVEL_PLOT_COLORS[lvl])
                                series_tag = dpg.add_scatter_series([], [], label=lvl)
                                self._plot_series[lvl] = series_tag

                                # per-series colour theme
                                with dpg.theme() as s_theme:
                                    with dpg.theme_component(dpg.mvScatterSeries):
                                        dpg.add_theme_color(dpg.mvPlotCol_MarkerFill, col255, category=dpg.mvThemeCat_Plots)
                                        dpg.add_theme_color(dpg.mvPlotCol_MarkerOutline, col255, category=dpg.mvThemeCat_Plots)
                                        dpg.add_theme_style(dpg.mvPlotStyleVar_MarkerSize, 5, category=dpg.mvThemeCat_Plots)
                                dpg.bind_item_theme(series_tag, s_theme)

            # ---- timeline hover tooltip ----
            with dpg.window(
                tag=self._timeline_tooltip_window,
                show=False,
                no_title_bar=True,
                no_resize=True,
                no_move=True,
                no_background=True,
                no_scrollbar=True,
                no_collapse=True,
                no_saved_settings=True,
                no_focus_on_appearing=True,
                autosize=True,
            ):
                dpg.add_text("", tag=self._timeline_tooltip_header, color=(139, 233, 253, 255))
                dpg.add_text("", tag=self._timeline_tooltip_body, color=(220, 220, 230, 255))

        # ---- Enhanced button themes ----
        with dpg.theme() as start_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (46, 160, 67, 255))         # Modern green
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (72, 187, 120, 255)) # Bright green
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (34, 139, 34, 255))   # Forest green
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))         # White text
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
        dpg.bind_item_theme("btn_start", start_theme)

        with dpg.theme() as stop_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (220, 53, 69, 255))         # Modern red
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (248, 81, 73, 255))  # Bright red
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (176, 42, 55, 255))   # Deep red
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))         # White text
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
        dpg.bind_item_theme("btn_stop", stop_theme)
        
        # Export and utility button theme
        with dpg.theme() as utility_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (68, 71, 90, 255))          # Modern grey-blue
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (98, 114, 164, 255)) # Bright periwinkle
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (80, 250, 123, 255))  # Active green
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
        dpg.bind_item_theme("btn_export_csv", utility_theme)
        dpg.bind_item_theme("btn_toggle_stats", utility_theme)
        
        logger.info("UI build completed successfully")

    # -- run loop -----------------------------------------------------------
    def run(self) -> None:
        """Initialize and run the main application event loop."""
        try:
            dpg.create_viewport(title="[UARTIUM] Enterprise UART Monitor v1.0", width=1280, height=900, resizable=True)
            dpg.setup_dearpygui()
            dpg.set_primary_window("primary_window", True)
            dpg.show_viewport()
            dpg.maximize_viewport()  # Start maximized for best experience
            logger.info("Uartium application started successfully")
        except Exception as e:
            logger.error(f"Failed to initialize UI: {e}")
            raise

        # main render loop with message polling
        while dpg.is_dearpygui_running():
            self._poll_messages()
            self._update_timeline_hover()
            dpg.render_dearpygui_frame()

        # cleanup
        self.backend.stop()
        dpg.destroy_context()

    # -- callbacks ----------------------------------------------------------
    def _on_theme_changed(self, sender, app_data) -> None:
        """Callback when user changes theme."""
        try:
            theme_name = "dark" if "DARK" in app_data else "light"
            self._apply_theme(theme_name)
            self._save_settings()
            status_msg = f"Theme changed to {theme_name.capitalize()}"
            dpg.set_value(self._status_text, status_msg)
            dpg.configure_item(self._status_text, color=(139, 233, 253, 255))
            logger.info(f"Theme changed to: {theme_name}")
        except Exception as e:
            logger.error(f"Error changing theme: {e}")
            self._set_error(f"Theme change failed: {e}")
    
    def _on_filter_changed(self, sender, app_data, user_data) -> None:
        """Callback when user toggles a level filter."""
        level = user_data
        self._level_filters[level] = app_data
        self._refresh_timeline()
        self._save_settings()
    
    def _on_baud_changed(self, sender, app_data) -> None:
        """Callback when user changes the baud rate input.
        If serial backend is running, restart connection with new baud rate.
        """
        try:
            new_baud = int(app_data)
        except (ValueError, TypeError):
            new_baud = self._initial_baudrate
        
        self._selected_baudrate = new_baud
        
        # If serial backend is running, restart with new baud rate
        if self._is_serial_backend and self.backend.is_running:
            self.backend.stop()
            self.backend.baudrate = self._selected_baudrate
            self.backend.start()
            dpg.set_value(self._status_text, f"●  Running @ {self._selected_baudrate} baud")
            dpg.configure_item(self._status_text, color=(80, 250, 123, 255))

    def _on_start(self) -> None:
        """Start serial monitoring with error handling and recovery."""
        try:
            # Validate port name
            port = dpg.get_value("port_input").strip()
            if not port:
                self._set_error("[ERROR] Port name cannot be empty")
                return
            
            # Update baud rate on SerialBackend before starting
            if self._is_serial_backend:
                self.backend.baudrate = self._selected_baudrate
            
            self.backend.start()
            self._start_time = time.time()
            self._session_start_time = time.time()
            self._is_running = True
            self._reconnect_attempts = 0
            self._error_count = 0
            
            dpg.configure_item("btn_start", enabled=False)
            dpg.configure_item("btn_stop", enabled=True)
            dpg.set_value(self._status_text, f"Active - {port} @ {self._selected_baudrate} baud")
            dpg.configure_item(self._status_text, color=(80, 250, 123, 255))
            logger.info(f"Serial monitoring started on {port} @ {self._selected_baudrate} baud")
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self._set_error(f"[ERROR] Start failed: {e}")
            self._is_running = False

    def _on_stop(self) -> None:
        """Stop serial monitoring with graceful shutdown."""
        try:
            self.backend.stop()
            dpg.configure_item("btn_start", enabled=True)
            dpg.configure_item("btn_stop", enabled=False)
            dpg.set_value(self._status_text, "Stopped")
            dpg.configure_item(self._status_text, color=(180, 180, 180, 255))
            self._is_running = False
            logger.info("Serial monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            self._set_error(f"[ERROR] Stop failed: {e}")

    # -- message pump -------------------------------------------------------
    def _poll_messages(self) -> None:
        """Drain all pending messages from the backend into the GUI."""
        batch = 0
        batch_start = time.time()
        while batch < 50:  # cap per frame to stay responsive
            msg = self.backend.read_message()
            if msg is None:
                break
            level = msg["level"]
            self._level_counts[level] += 1
            self._add_log_line(msg)
            self._add_timeline_point(msg)
            # Update data monitor for any message with variables
            if "data_fields" in msg:
                self._update_data_monitor(msg["data_fields"], level)
            batch += 1
        
        # Update statistics display every second
        current_time = time.time()
        if current_time - self._last_stats_update >= 1.0:
            self._update_statistics()
            self._last_stats_update = current_time
    
    def _update_statistics(self) -> None:
        """Update the statistics display with current message counts and performance metrics."""
        if hasattr(self, '_stat_info'):
            try:
                dpg.set_value(self._stat_info, f"INFO: {self._level_counts['INFO']}")
                dpg.set_value(self._stat_warn, f"WARN: {self._level_counts['WARNING']}")
                dpg.set_value(self._stat_error, f"ERROR: {self._level_counts['ERROR']}")
                dpg.set_value(self._stat_debug, f"DEBUG: {self._level_counts['DEBUG']}")
                
                # Calculate message rate and uptime
                if self._start_time and self._session_start_time:
                    elapsed = time.time() - self._start_time
                    total_msgs = sum(self._level_counts.values())
                    rate = total_msgs / elapsed if elapsed > 0 else 0.0
                    
                    # Calculate uptime in HH:MM:SS format
                    uptime_seconds = int(time.time() - self._session_start_time)
                    uptime_h = uptime_seconds // 3600
                    uptime_m = (uptime_seconds % 3600) // 60
                    uptime_s = uptime_seconds % 60
                    uptime_str = f"{uptime_h:02d}:{uptime_m:02d}:{uptime_s:02d}"
                    
                    dpg.set_value(self._stat_rate, 
                        f"Rate: {rate:.2f} msg/sec | Total: {total_msgs} msgs | Errors: {self._error_count}")
                    
                    # Update status bar uptime
                    if hasattr(self, '_status_uptime'):
                        dpg.set_value(self._status_uptime, f"Uptime: {uptime_str}")
            except Exception as e:
                logger.error(f"Error updating statistics: {e}")
    
    def _refresh_timeline(self) -> None:
        """Refresh all timeline series based on current filter settings."""
        for level in LEVEL_Y:
            series_tag = self._plot_series.get(level)
            if series_tag:
                if self._level_filters[level]:
                    # Show series
                    dpg.set_value(series_tag, [list(self._timeline_x[level]),
                                                list(self._timeline_y[level])])
                else:
                    # Hide series
                    dpg.set_value(series_tag, [[], []])

    def _add_log_line(self, msg: dict) -> None:
        """Add a formatted log line with validation and error handling."""
        try:
            level = msg.get("level", "INFO")
            if level not in LEVEL_COLORS:
                level = "INFO"
                self._error_count += 1
            
            color = LEVEL_COLORS.get(level, (200, 200, 200, 255))
            badge = LEVEL_BADGE.get(level, "[???]    ")
            ts = time.strftime("%H:%M:%S", time.localtime(msg.get("timestamp", time.time())))
            text = msg.get('text', '<no message>')
            line = f"{ts}  {badge} {text}"

            self._msg_count += 1

            # trim oldest lines to keep memory bounded
            if self._msg_count > MAX_LOG_LINES:
                children = dpg.get_item_children(self._log_parent, slot=1)
                if children:
                    dpg.delete_item(children[0])

            # Add main message line
            dpg.add_text(line, parent=self._log_parent, color=color)

            # Add variables below if present - colored by message level
            if "data_fields" in msg and msg["data_fields"]:
                indent = "    "
                for var_name, info in msg["data_fields"].items():
                    val_str = str(info.get("value", "N/A"))
                    type_str = info.get("type", "str")
                    var_line = f"{indent}{var_name}:{type_str} = {val_str}"
                    dpg.add_text(var_line, parent=self._log_parent, color=color)
        except Exception as e:
            logger.error(f"Error adding log line: {e}")
            self._error_count += 1

    def _add_timeline_point(self, msg: dict) -> None:
        level = msg["level"]
        if self._start_time is None:
            return
        elapsed = msg["timestamp"] - self._start_time
        y = LEVEL_Y.get(level, 2.0)

        self._timeline_x[level].append(elapsed)
        self._timeline_y[level].append(y)
        self._timeline_messages[level].append(msg)

        # update the scatter series data only if filter is enabled
        series_tag = self._plot_series.get(level)
        if series_tag and self._level_filters[level]:
            dpg.set_value(series_tag, [list(self._timeline_x[level]),
                                        list(self._timeline_y[level])])

        # auto-fit x-axis
        dpg.fit_axis_data(self._x_axis_tag)

    def _update_timeline_hover(self) -> None:
        """Show a tooltip when hovering near a timeline point."""
        if not dpg.does_item_exist("timeline_plot"):
            return

        # Hide tooltip if mouse is over the tooltip window itself
        if dpg.does_item_exist(self._timeline_tooltip_window) and dpg.is_item_hovered(self._timeline_tooltip_window):
            dpg.configure_item(self._timeline_tooltip_window, show=False)
            self._last_hovered_msg_id = None
            self._timeline_tooltip_pos = None
            self._pinned_msg = None
            return

        # Use plot bounds to determine hover (more reliable than is_item_hovered)
        try:
            mx_screen, my_screen = dpg.get_mouse_pos()
            rect_min = dpg.get_item_rect_min("timeline_plot")
            rect_max = dpg.get_item_rect_max("timeline_plot")
            if not (rect_min[0] <= mx_screen <= rect_max[0] and rect_min[1] <= my_screen <= rect_max[1]):
                if dpg.does_item_exist(self._timeline_tooltip_window):
                    dpg.configure_item(self._timeline_tooltip_window, show=False)
                self._last_hovered_msg_id = None
                self._timeline_tooltip_pos = None
                self._pinned_msg = None
                return
        except Exception:
            return

        # Try both plot mouse APIs for compatibility
        try:
            mouse_x, mouse_y = dpg.get_plot_mouse_pos("timeline_plot")
        except Exception:
            try:
                mouse_x, mouse_y = dpg.get_plot_mouse_pos()
            except Exception:
                return

        # Determine hover radius in plot units based on ~10px tolerance
        try:
            rect_width = max(1.0, rect_max[0] - rect_min[0])
            rect_height = max(1.0, rect_max[1] - rect_min[1])
            x_min, x_max = dpg.get_axis_limits(self._x_axis_tag)
            y_min, y_max = dpg.get_axis_limits("timeline_y_axis")
            x_range = max(0.001, x_max - x_min)
            y_range = max(0.001, y_max - y_min)
            max_dx = x_range * (6.0 / rect_width)
            max_dy = y_range * (6.0 / rect_height)
        except Exception:
            max_dx = 1.0
            max_dy = 0.9

        best_msg = None
        best_level = None
        best_dx = None
        best_x = None
        best_y = None

        for level in LEVEL_Y:
            if not self._level_filters.get(level, True):
                continue
            level_y = LEVEL_Y[level]
            if abs(mouse_y - level_y) > max_dy:
                continue

            x_list = self._timeline_x[level]
            if not x_list:
                continue

            # Find nearest point on this level by x distance
            for idx, x_val in enumerate(x_list):
                dx = abs(mouse_x - x_val)
                if dx <= max_dx and (best_dx is None or dx < best_dx):
                    best_dx = dx
                    best_level = level
                    best_msg = self._timeline_messages[level][idx]
                    best_x = x_val
                    best_y = level_y

        # Click to pin full details (message + variables)
        if dpg.is_item_clicked("timeline_plot"):
            if best_msg is not None:
                self._pinned_msg = best_msg
                ts = time.strftime("%H:%M:%S", time.localtime(best_msg.get("timestamp", time.time())))
                header = f"{ts}  {best_level}"
                lines = [best_msg.get("text", "").strip() or "(no message)"]
                data_fields = best_msg.get("data_fields", {})
                if data_fields:
                    lines.append("")
                    for var_name, info in data_fields.items():
                        val_str = str(info.get("value", "N/A"))
                        type_str = info.get("type", "str")
                        lines.append(f"{var_name}:{type_str} = {val_str}")
                dpg.set_value(self._timeline_tooltip_header, header)
                dpg.set_value(self._timeline_tooltip_body, "\n".join(lines))
                try:
                    mx_screen, my_screen = dpg.get_mouse_pos()
                    self._timeline_tooltip_pos = (int(mx_screen) + 12, int(my_screen) + 12)
                except Exception:
                    self._timeline_tooltip_pos = None
            else:
                self._pinned_msg = None

        # Hover shows only the message (no variables), unless pinned
        if self._pinned_msg is None:
            if best_msg is None:
                if dpg.does_item_exist(self._timeline_tooltip_window):
                    dpg.configure_item(self._timeline_tooltip_window, show=False)
                self._last_hovered_msg_id = None
                self._timeline_tooltip_pos = None
                return

            msg_id = id(best_msg)
            if msg_id != self._last_hovered_msg_id:
                ts = time.strftime("%H:%M:%S", time.localtime(best_msg.get("timestamp", time.time())))
                header = f"{ts}  {best_level}"
                line = best_msg.get("text", "").strip() or "(no message)"
                dpg.set_value(self._timeline_tooltip_header, header)
                dpg.set_value(self._timeline_tooltip_body, line)
                self._last_hovered_msg_id = msg_id
                try:
                    mx_screen, my_screen = dpg.get_mouse_pos()
                    self._timeline_tooltip_pos = (int(mx_screen) + 12, int(my_screen) + 12)
                except Exception:
                    self._timeline_tooltip_pos = None

        # Place tooltip at stored position (anchored to first hover/click)
        if dpg.does_item_exist(self._timeline_tooltip_window):
            if self._timeline_tooltip_pos:
                dpg.configure_item(self._timeline_tooltip_window, show=True)
                dpg.set_item_pos(self._timeline_tooltip_window, list(self._timeline_tooltip_pos))
            else:
                dpg.configure_item(self._timeline_tooltip_window, show=True)

    def _update_data_monitor(self, fields: dict, level: str) -> None:
        """Update the Data Monitor table with the latest variable values.
        Colors are based on the source message level.
        """
        color = LEVEL_COLORS.get(level, (200, 200, 200, 255))
        
        for var_name, info in fields.items():
            val_str = str(info["value"])
            type_str = info.get("type", "str")

            if var_name in self._data_table_rows:
                # update existing row cells
                _, type_cell, value_cell = self._data_table_rows[var_name]
                dpg.set_value(type_cell, type_str)
                dpg.set_value(value_cell, val_str)
            else:
                # add a new row to the table
                with dpg.table_row(parent="data_table"):
                    name_cell = dpg.add_text(var_name, color=color)
                    type_cell = dpg.add_text(type_str, color=color)
                    value_cell = dpg.add_text(val_str, color=color)
                self._data_table_rows[var_name] = (name_cell, type_cell, value_cell)

            self._data_vars[var_name] = info

    def _export_to_csv(self) -> None:
        """Export all messages and variables to CSV file with validation."""
        import csv
        
        try:
            filename = f"uartium_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['TIMESTAMP', 'EVENT_LEVEL', 'MESSAGE_TEXT', 'VARIABLE_NAME', 'VARIABLE_VALUE', 'VARIABLE_TYPE'])
                
                # Export from timeline messages (most complete data)
                for level in LEVEL_Y:
                    for msg in self._timeline_messages.get(level, []):
                        # Use device timestamp if available, otherwise PC timestamp
                        ts = msg.get('device_timestamp', int(msg.get('timestamp', time.time())))
                        message_text = msg.get('text', '')
                        
                        # If message has variables, export each variable as a separate row
                        if 'data_fields' in msg and msg['data_fields']:
                            for var_name, var_info in msg['data_fields'].items():
                                writer.writerow([
                                    ts,
                                    level,
                                    message_text,
                                    var_name,
                                    var_info.get('value', 'N/A'),
                                    var_info.get('type', 'str')
                                ])
                        else:
                            # No variables - export message only
                            writer.writerow([
                                ts,
                                level,
                                message_text,
                                '',
                                '',
                                ''
                            ])
            
            logger.info(f"Data exported to {filename}")
            dpg.set_value(self._status_text, f"[OK] Exported to {filename}")
            dpg.configure_item(self._status_text, color=(80, 250, 123, 255))
        except Exception as e:
            logger.error(f"Export failed: {e}")
            self._set_error(f"Export failed: {e}")
    
    def _toggle_statistics(self) -> None:
        """Toggle statistics panel visibility."""
        self._stats_visible = not self._stats_visible
        if dpg.does_item_exist("stats_panel"):
            dpg.configure_item("stats_panel", show=self._stats_visible)
        self._save_settings()
        logger.info(f"Statistics panel toggled: {self._stats_visible}")
    
    def _set_error(self, error_msg: str) -> None:
        """Set error status with thread-safe locking."""
        with self._error_lock:
            self._last_error = error_msg
            self._error_count += 1
            dpg.set_value(self._status_text, error_msg)
            dpg.configure_item(self._status_text, color=(255, 82, 82, 255))
            logger.warning(error_msg)
