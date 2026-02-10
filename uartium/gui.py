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
from uartium.ui_log_data import build_log_and_data
from uartium.ui_settings import build_settings_window
from uartium.ui_stats import build_stats_panel
from uartium.ui_timeline import build_timeline_panel, build_timeline_tooltip
from uartium.ui_toolbar import build_toolbar
from uartium.ui_tags import (
    TAG_BTN_EXPORT_CSV,
    TAG_BTN_SETTINGS,
    TAG_BTN_SETTINGS_OVERLAY,
    TAG_BTN_START,
    TAG_BTN_STOP,
    TAG_BTN_TOGGLE_STATS,
    TAG_DATA_TABLE,
    TAG_LOG_WINDOW,
    TAG_MODE_RADIO,
    TAG_PORT_INPUT,
    TAG_STATS_PANEL,
    TAG_STATUS_ROW,
    TAG_TIMELINE_PLOT,
    TAG_TIMELINE_Y_AXIS,
)

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
        self.backend = backend
        self._initial_baudrate = initial_baudrate
        self._selected_baudrate = initial_baudrate
        self._is_serial_backend = isinstance(backend, SerialBackend)
        self._use_demo = backend is None
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
                # Try loading Segoe MDL2 Assets for Windows icon glyphs (gear, etc.)
                try:
                    self._icon_font = dpg.add_font("C:/Windows/Fonts/segmdl2.ttf", 18)
                except Exception:
                    # font not available; proceed without icon font
                    self._icon_font = None
            except:
                # Fallback - use default DearPyGui font
                self._icon_font = None

        # ---- global theme ----
        self._apply_theme()

        # ---- settings window (hidden by default) ----
        build_settings_window(self)

        # ---- main viewport window ----
        with dpg.window(tag="primary_window"):
            # ===== CLEAN TOOLBAR - Arduino IDE Style =====
            build_toolbar(self)

            # ===== COLLAPSIBLE STATISTICS PANEL =====
            build_stats_panel(self, LEVEL_COLORS)

            dpg.add_spacer(height=8)

            # ===== MAIN CONTENT AREA - TWO COLUMN LAYOUT =====
            with dpg.group(horizontal=True):
                build_log_and_data(self)
                dpg.add_spacer(width=8)
                build_timeline_panel(self, LEVEL_Y, LEVEL_PLOT_COLORS)

            # ---- timeline hover tooltip ----
            build_timeline_tooltip(self)

        # ---- Enhanced button themes ----
        with dpg.theme() as start_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (46, 160, 67, 255))         # Modern green
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (72, 187, 120, 255)) # Bright green
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (34, 139, 34, 255))   # Forest green
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))         # White text
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
        dpg.bind_item_theme(TAG_BTN_START, start_theme)

        with dpg.theme() as stop_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (220, 53, 69, 255))         # Modern red
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (248, 81, 73, 255))  # Bright red
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (176, 42, 55, 255))   # Deep red
                dpg.add_theme_color(dpg.mvThemeCol_Text, (255, 255, 255, 255))         # White text
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
        dpg.bind_item_theme(TAG_BTN_STOP, stop_theme)
        
        # Export and utility button theme
        with dpg.theme() as utility_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (68, 71, 90, 255))          # Modern grey-blue
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (98, 114, 164, 255)) # Bright periwinkle
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (80, 250, 123, 255))  # Active green
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
        dpg.bind_item_theme(TAG_BTN_EXPORT_CSV, utility_theme)
        dpg.bind_item_theme(TAG_BTN_TOGGLE_STATS, utility_theme)
        dpg.bind_item_theme(TAG_BTN_SETTINGS, utility_theme)

        # Compact theme for the status row to reduce vertical footprint
        with dpg.theme() as _status_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 6, 2)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 4, 2)
        dpg.bind_item_theme(TAG_STATUS_ROW, _status_theme)

        logger.info("UI build completed successfully")

        # (Removed floating overlay) Help button lives in the main toolbar for consistent layout
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
            # Position floating settings overlay in top-right and bring to front
            try:
                if dpg.does_item_exist("floating_settings_win"):
                    try:
                        vw = dpg.get_viewport_width()
                        vh = dpg.get_viewport_height()
                    except Exception:
                        vw = 1280
                        vh = 900
                    margin = 8
                    # try to measure the button width, fallback to a conservative value
                    try:
                        btn_w = dpg.get_item_width(TAG_BTN_SETTINGS_OVERLAY) or 44
                    except Exception:
                        btn_w = 44
                    x = max(margin, vw - btn_w - margin)
                    y = margin
                    dpg.set_item_pos("floating_settings_win", [int(x), int(y)])
                    dpg.bring_item_to_front("floating_settings_win")
            except Exception:
                pass
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
            # Ensure backend exists
            if self.backend is None:
                self._set_error("[ERROR] No backend configured")
                return
            
            # For real serial, validate and update port
            if self._is_serial_backend:
                port = dpg.get_value(TAG_PORT_INPUT).strip()
                if not port:
                    self._set_error("[ERROR] Port name cannot be empty")
                    return
                self.backend.port = port
                self.backend.baudrate = self._selected_baudrate
                status_msg = f"Active - {port} @ {self._selected_baudrate} baud"
            else:
                # Demo mode
                status_msg = "Active - Demo Mode"
            
            self.backend.start()
            self._start_time = time.time()
            self._session_start_time = time.time()
            self._is_running = True
            self._reconnect_attempts = 0
            self._error_count = 0
            
            dpg.configure_item(TAG_BTN_START, enabled=False)
            dpg.configure_item(TAG_BTN_STOP, enabled=True)
            dpg.set_value(self._status_text, status_msg)
            dpg.configure_item(self._status_text, color=(80, 250, 123, 255))
            logger.info(f"Serial monitoring started: {status_msg}")
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            self._set_error(f"[ERROR] Start failed: {e}")
            self._is_running = False

    def _on_stop(self) -> None:
        """Stop serial monitoring with graceful shutdown."""
        try:
            self.backend.stop()
            dpg.configure_item(TAG_BTN_START, enabled=True)
            dpg.configure_item(TAG_BTN_STOP, enabled=False)
            dpg.set_value(self._status_text, "Stopped")
            dpg.configure_item(self._status_text, color=(180, 180, 180, 255))
            self._is_running = False
            logger.info("Serial monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}")
            self._set_error(f"[ERROR] Stop failed: {e}")

    def _on_mode_changed(self, sender, value) -> None:
        """Switch between demo and real serial mode."""
        if self._is_running:
            self._set_error("[ERROR] Stop monitoring before changing mode")
            return
        
        if value == "Demo":
            self.backend = DemoSerialBackend(interval=0.5)
            self._use_demo = True
            self._is_serial_backend = False
            logger.info("Switched to Demo mode")
            self._set_error("[INFO] Switched to Demo mode")
        else:  # Real Serial
            port = dpg.get_value(TAG_PORT_INPUT).strip()
            if not port:
                self._set_error("[ERROR] Port name cannot be empty for Real Serial mode")
                dpg.set_value(TAG_MODE_RADIO, "Demo")
                return
            self.backend = SerialBackend(port=port, baudrate=self._selected_baudrate)
            self._use_demo = False
            self._is_serial_backend = True
            logger.info(f"Switched to Real Serial mode: {port} @ {self._selected_baudrate}")
            self._set_error(f"[INFO] Switched to Real Serial: {port} @ {self._selected_baudrate}")

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
            text = msg.get('text', '')
            
            # Debug logging
            logger.debug(f"_add_log_line - text: {repr(text)}, has_data: {'data_fields' in msg}")
            
            # Build the log line - only include text if it's not empty
            if text:
                line = f"{ts}  {badge} {text}"
            else:
                line = f"{ts}  {badge}"

            self._msg_count += 1

            # trim oldest lines to keep memory bounded
            if self._msg_count > MAX_LOG_LINES:
                children = dpg.get_item_children(self._log_parent, slot=1)
                if children:
                    dpg.delete_item(children[0])

            # Add message and variables in a compact group (message first, then variables)
            with dpg.group(parent=self._log_parent, horizontal=False):
                # Main message line
                dpg.add_text(line, color=color)

                # Variables below if present
                if "data_fields" in msg and msg["data_fields"]:
                    for var_name, info in msg["data_fields"].items():
                        val_str = str(info.get("value", "N/A"))
                        var_line = f"    {var_name} = {val_str}"
                        dpg.add_text(var_line, color=color)
            # Apply compact spacing theme to the entire message group
            with dpg.theme() as compact_theme:
                with dpg.theme_component(dpg.mvAll):
                    dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 1)
            dpg.bind_item_theme(dpg.last_container(), compact_theme)
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
        if not dpg.does_item_exist(TAG_TIMELINE_PLOT):
            return

        # Check if mouse is outside the plot area
        try:
            mx_screen, my_screen = dpg.get_mouse_pos()
            rect_min = dpg.get_item_rect_min(TAG_TIMELINE_PLOT)
            rect_max = dpg.get_item_rect_max(TAG_TIMELINE_PLOT)
            
            if not (rect_min[0] <= mx_screen <= rect_max[0] and rect_min[1] <= my_screen <= rect_max[1]):
                # Mouse left the plot - hide tooltip
                if dpg.does_item_exist(self._timeline_tooltip_window):
                    dpg.configure_item(self._timeline_tooltip_window, show=False)
                self._last_hovered_msg_id = None
                self._timeline_tooltip_pos = None
                self._pinned_msg = None
                return

            # If mouse is over the tooltip window, hide it to avoid overlap glitches
            if dpg.does_item_exist(self._timeline_tooltip_window):
                try:
                    tip_min = dpg.get_item_rect_min(self._timeline_tooltip_window)
                    tip_max = dpg.get_item_rect_max(self._timeline_tooltip_window)
                    if tip_min and tip_max:
                        if tip_min[0] <= mx_screen <= tip_max[0] and tip_min[1] <= my_screen <= tip_max[1]:
                            dpg.configure_item(self._timeline_tooltip_window, show=False)
                            self._last_hovered_msg_id = None
                            self._timeline_tooltip_pos = None
                            self._pinned_msg = None
                            return
                except Exception:
                    pass
        except Exception:
            return

        # Try both plot mouse APIs for compatibility
        try:
            mouse_x, mouse_y = dpg.get_plot_mouse_pos(TAG_TIMELINE_PLOT)
        except Exception:
            try:
                mouse_x, mouse_y = dpg.get_plot_mouse_pos()
            except Exception:
                return

        # Determine hover radius in plot units based on pixel tolerance
        try:
            rect_width = max(1.0, rect_max[0] - rect_min[0])
            rect_height = max(1.0, rect_max[1] - rect_min[1])
            x_min, x_max = dpg.get_axis_limits(self._x_axis_tag)
            y_min, y_max = dpg.get_axis_limits(TAG_TIMELINE_Y_AXIS)
            x_range = max(0.001, x_max - x_min)
            y_range = max(0.001, y_max - y_min)
            # Smaller radius to acquire hover, larger radius to keep it (prevents flicker)
            max_dx_show = x_range * (10.0 / rect_width)
            max_dy_show = y_range * (10.0 / rect_height)
            max_dx_hide = x_range * (14.0 / rect_width)
            max_dy_hide = y_range * (14.0 / rect_height)
            # If mouse is over axes (outside data area), hide immediately
            if mouse_x < x_min or mouse_x > x_max or mouse_y < y_min or mouse_y > y_max:
                if dpg.does_item_exist(self._timeline_tooltip_window):
                    dpg.configure_item(self._timeline_tooltip_window, show=False)
                self._last_hovered_msg_id = None
                self._timeline_tooltip_pos = None
                if self._pinned_msg is None:
                    return
        except Exception:
            max_dx_show = 1.0
            max_dy_show = 0.9
            max_dx_hide = 1.4
            max_dy_hide = 1.3

        best_msg = None
        best_level = None
        best_dx = None
        best_x = None
        best_y = None

        last_msg_id = self._last_hovered_msg_id

        for level in LEVEL_Y:
            if not self._level_filters.get(level, True):
                continue
            level_y = LEVEL_Y[level]

            x_list = self._timeline_x[level]
            if not x_list:
                continue

            # Find nearest point on this level by x distance
            for idx, x_val in enumerate(x_list):
                dx = abs(mouse_x - x_val)
                msg = self._timeline_messages[level][idx]
                msg_id = id(msg)
                dy = abs(mouse_y - level_y)
                within_show = dx <= max_dx_show and dy <= max_dy_show
                within_hide = msg_id == last_msg_id and dx <= max_dx_hide and dy <= max_dy_hide
                if (within_show or within_hide) and (best_dx is None or dx < best_dx):
                    best_dx = dx
                    best_level = level
                    best_msg = msg
                    best_x = x_val
                    best_y = level_y
        # If no dot found, hide tooltip
        if best_msg is None:
            if dpg.does_item_exist(self._timeline_tooltip_window):
                dpg.configure_item(self._timeline_tooltip_window, show=False)
            self._last_hovered_msg_id = None
            self._timeline_tooltip_pos = None
            self._pinned_msg = None
            return


        # Clicking no longer pins messages; hovering alone controls the tooltip

        # Hover shows only the message (no variables), unless pinned
        if self._pinned_msg is None:
            msg_id = id(best_msg)
            # Update content and position only when switching to a different message
            if msg_id != self._last_hovered_msg_id:
                ts = time.strftime("%H:%M:%S", time.localtime(best_msg.get("timestamp", time.time())))
                header = f"{ts}  {best_level}"
                line = best_msg.get("text", "").strip() or "(no message)"
                dpg.set_value(self._timeline_tooltip_header, header)
                dpg.set_value(self._timeline_tooltip_body, line)
                self._last_hovered_msg_id = msg_id
                # Always position tooltip at the top-right inside the plot and show it
                try:
                    rect_min = dpg.get_item_rect_min(TAG_TIMELINE_PLOT)
                    rect_max = dpg.get_item_rect_max(TAG_TIMELINE_PLOT)
                    tooltip_w = 120
                    padding = 12
                    tooltip_x = rect_max[0] - tooltip_w - padding
                    tooltip_y = rect_min[1] + padding
                    self._timeline_tooltip_pos = (int(tooltip_x), int(tooltip_y))
                    if dpg.does_item_exist(self._timeline_tooltip_window):
                        dpg.set_item_pos(self._timeline_tooltip_window, list(self._timeline_tooltip_pos))
                        dpg.configure_item(self._timeline_tooltip_window, show=True)
                except Exception:
                    # Fallback to a default position and show
                    self._timeline_tooltip_pos = (800, 200)
                    if dpg.does_item_exist(self._timeline_tooltip_window):
                        try:
                            dpg.set_item_pos(self._timeline_tooltip_window, list(self._timeline_tooltip_pos))
                            dpg.configure_item(self._timeline_tooltip_window, show=True)
                        except Exception:
                            pass

        # Place tooltip at stored position (anchored to the dot)
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
                with dpg.table_row(parent=TAG_DATA_TABLE):
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
        if dpg.does_item_exist(TAG_STATS_PANEL):
            dpg.configure_item(TAG_STATS_PANEL, show=self._stats_visible)
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
