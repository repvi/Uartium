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
from uartium import colors
from uartium.ui_log_data import build_log_and_data
from uartium.ui_settings import build_settings_window
from uartium.ui_stats import build_stats_window
from uartium.ui_timeline import build_timeline_panel, build_timeline_tooltip
from uartium.ui_toolbar import build_toolbar
from uartium.ui_graphs import build_graph_panel, update_graph_data
from uartium.triggers import TriggerEngine
from uartium.ui_triggers import build_triggers_window, update_trigger_history
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
    TAG_SETTINGS_WINDOW,
    TAG_STATS_WINDOW,
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

# Import color definitions from centralized colors module
LEVEL_COLORS = colors.LEVEL_COLORS
DARK_THEME = colors.DARK_THEME
LIGHT_THEME = colors.LIGHT_THEME
LEVEL_PLOT_COLORS = colors.LEVEL_PLOT_COLORS

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
        self._load_settings()

        # Initialize trigger engine
        self._trigger_engine = TriggerEngine()
        self._trigger_engine.on_visual_alert = self._handle_visual_alert
        self._trigger_engine.on_log_trigger = self._handle_log_trigger
        # Audio handler (added) - plays a short OS-specific sound or falls back to terminal bell
        self._trigger_engine.on_audio_alert = self._handle_audio_alert
        self._trigger_alerts = []  # Active visual alerts

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

        # ---- triggers window (hidden by default) ----
        build_triggers_window(self)

        # ---- statistics window (hidden by default) ----
        build_stats_window(self, LEVEL_COLORS)

        # ---- main viewport window ----
        with dpg.window(tag="primary_window"):
            # ===== CLEAN TOOLBAR - Arduino IDE Style =====
            build_toolbar(self)

            dpg.add_spacer(height=8)

            # ===== MAIN CONTENT AREA - THREE COLUMN LAYOUT =====
            with dpg.group(horizontal=True):
                build_log_and_data(self)
                dpg.add_spacer(width=8)
                build_timeline_panel(self, LEVEL_Y, LEVEL_PLOT_COLORS)
                dpg.add_spacer(width=8)
                build_graph_panel(self)

            # ---- timeline hover tooltip ----
            build_timeline_tooltip(self)

        # ---- Enhanced button themes ----
        with dpg.theme() as start_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, colors.START_BUTTON_DEFAULT)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, colors.START_BUTTON_HOVERED)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, colors.START_BUTTON_ACTIVE)
                dpg.add_theme_color(dpg.mvThemeCol_Text, colors.START_BUTTON_TEXT)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
        dpg.bind_item_theme(TAG_BTN_START, start_theme)

        with dpg.theme() as stop_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, colors.STOP_BUTTON_DEFAULT)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, colors.STOP_BUTTON_HOVERED)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, colors.STOP_BUTTON_ACTIVE)
                dpg.add_theme_color(dpg.mvThemeCol_Text, colors.STOP_BUTTON_TEXT)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
        dpg.bind_item_theme(TAG_BTN_STOP, stop_theme)

        # Export and utility button theme
        with dpg.theme() as utility_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, colors.UTILITY_BUTTON_DEFAULT)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, colors.UTILITY_BUTTON_HOVERED)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, colors.UTILITY_BUTTON_ACTIVE)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6)
        dpg.bind_item_theme(TAG_BTN_EXPORT_CSV, utility_theme)
        dpg.bind_item_theme(TAG_BTN_TOGGLE_STATS, utility_theme)
        dpg.bind_item_theme(TAG_BTN_SETTINGS, utility_theme)
        dpg.bind_item_theme("btn_triggers", utility_theme)

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
            dpg.configure_item(self._status_text, color=colors.STATUS_INFO)
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
            dpg.configure_item(self._status_text, color=colors.STATUS_RUNNING)

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
            dpg.configure_item(self._status_text, color=colors.STATUS_RUNNING)
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
            dpg.configure_item(self._status_text, color=colors.STATUS_STOPPED)
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
            # Update data monitor and graphs for any message with variables
            if "data_fields" in msg:
                self._update_data_monitor(msg["data_fields"], level)
                # Update graph data for numeric variables
                if self._start_time:
                    elapsed = msg["timestamp"] - self._start_time
                    for var_name, info in msg["data_fields"].items():
                        var_type = info.get("type", "str")
                        value = info.get("value")
                        if var_type in ("uint", "int", "float", "timestamp") and value is not None:
                            try:
                                numeric_value = float(value)
                            except (ValueError, TypeError):
                                logger.debug(f"Skipping non-numeric variable {var_name!r} value={value!r} type={var_type!r}")
                                continue
                            update_graph_data(self, var_name, numeric_value, elapsed, var_type)

            # Evaluate triggers
            trigger_events = self._trigger_engine.evaluate_message(msg)
            for event in trigger_events:
                update_trigger_history(self, event)

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
                # Update individual level counts (just the number now, card has label)
                dpg.set_value(self._stat_info, str(self._level_counts['INFO']))
                dpg.set_value(self._stat_warn, str(self._level_counts['WARNING']))
                dpg.set_value(self._stat_error, str(self._level_counts['ERROR']))
                dpg.set_value(self._stat_debug, str(self._level_counts['DEBUG']))

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

                    # Update performance metrics in stats window
                    dpg.set_value(self._stat_rate, f"Rate: {rate:.2f} msg/sec")

                    # Update total messages
                    if hasattr(self, '_stat_total'):
                        dpg.set_value(self._stat_total, f"Total Messages: {total_msgs}")

                    # Update error count
                    if hasattr(self, '_stat_errors_total'):
                        dpg.set_value(self._stat_errors_total, f"Total Errors: {self._level_counts['ERROR']}")

                    # Update session time
                    if hasattr(self, '_stat_session_time'):
                        dpg.set_value(self._stat_session_time, f"Session Duration: {uptime_str}")

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

        # Check for clicks to reset state (fixes stuck tooltip bug)
        if dpg.is_mouse_button_clicked(dpg.mvMouseButton_Left):
            self._last_hovered_msg_id = None
            self._pinned_msg = None
            # Don't hide tooltip on click - let hover logic handle it

        # Check if mouse is outside the plot area
        try:
            mx_screen, my_screen = dpg.get_mouse_pos()
            rect_min = dpg.get_item_rect_min(TAG_TIMELINE_PLOT)
            rect_max = dpg.get_item_rect_max(TAG_TIMELINE_PLOT)

            if not (rect_min[0] <= mx_screen <= rect_max[0] and rect_min[1] <= my_screen <= rect_max[1]):
                # Mouse left the plot - hide tooltip and reset state
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
            dpg.configure_item(self._status_text, color=colors.STATUS_SUCCESS)
        except Exception as e:
            logger.error(f"Export failed: {e}")
            self._set_error(f"Export failed: {e}")
    
    def _toggle_statistics(self) -> None:
        """Open the statistics window."""
        if dpg.does_item_exist(TAG_STATS_WINDOW):
            dpg.show_item(TAG_STATS_WINDOW)
    
    def _set_error(self, error_msg: str) -> None:
        """Set error status with thread-safe locking."""
        with self._error_lock:
            self._last_error = error_msg
            self._error_count += 1
            dpg.set_value(self._status_text, error_msg)
            dpg.configure_item(self._status_text, color=colors.STATUS_ERROR)
            logger.warning(error_msg)

    # -- trigger alert handlers ---------------------------------------------
    def _handle_visual_alert(self, trigger_event) -> None:
        """Handle visual alert for trigger."""
        # Flash status bar with alert color
        alert_msg = f"[TRIGGER] {trigger_event.trigger_name}: {trigger_event.message}"
        dpg.set_value(self._status_text, alert_msg)
        dpg.configure_item(self._status_text, color=colors.STATUS_WARNING)
        logger.info(f"Trigger fired: {alert_msg}")

    def _handle_audio_alert(self, trigger_event) -> None:
        """Play an audio alert in a cross-platform way.

        This implementation:
        - Uses `winsound` on Windows
        - Uses `afplay` on macOS if available
        - On Linux prefers `paplay` or `aplay` if present, or `xdg-open` as last resort
        - If a custom audio file is configured (`self._audio_alert_file`) it will try to play it
          via the first available player. If `playsound` is installed it will use it in a
          background thread.
        - Final fallback: ASCII bell
        """
        import os
        import sys
        import threading
        import subprocess
        import shutil

        def _play_cmd(cmd: list[str]) -> None:
            try:
                subprocess.run(cmd, check=False)
            except Exception:
                pass

        try:
            # 1) Windows native beep
            if os.name == 'nt':
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                    return
                except Exception:
                    pass

            # 2) If a custom audio file is set, try to play it with available players
            audio_file = getattr(self, '_audio_alert_file', None)
            players = []
            # prefer platform-native players
            if sys.platform == 'darwin':
                players = [['afplay', audio_file]] if audio_file else [['afplay', '/System/Library/Sounds/Ping.aiff']]
            elif sys.platform.startswith('linux'):
                # paplay/aplay are common; xdg-open can open default app
                players = []
                if audio_file:
                    players.extend([['paplay', audio_file], ['aplay', audio_file], ['xdg-open', audio_file]])
                else:
                    # try standard freedesktop sounds
                    candidates = [
                        '/usr/share/sounds/freedesktop/stereo/complete.oga',
                        '/usr/share/sounds/freedesktop/stereo/alert.oga',
                        '/usr/share/sounds/ubuntu/stereo/desktop-login.ogg'
                    ]
                    for c in candidates:
                        if os.path.exists(c):
                            players.extend([['paplay', c], ['aplay', c]])
                            break
                    # fallback to xdg-open if nothing else
                    players.append(['xdg-open', audio_file or ''])
            else:
                # other POSIX (including mac fallback)
                if audio_file:
                    players = [['afplay', audio_file], ['xdg-open', audio_file]]
                else:
                    players = [['afplay', '/System/Library/Sounds/Ping.aiff']]

            # Try to find an available command and play
            for p in players:
                cmd_bin = p[0]
                if shutil.which(cmd_bin):
                    # For xdg-open, ensure file exists
                    if cmd_bin == 'xdg-open' and not audio_file:
                        continue
                    threading.Thread(target=_play_cmd, args=(p,), daemon=True).start()
                    return

            # 3) If playsound is installed and audio_file exists, use it
            if audio_file and os.path.exists(audio_file):
                try:
                    from playsound import playsound  # type: ignore
                    threading.Thread(target=playsound, args=(audio_file,), daemon=True).start()
                    return
                except Exception:
                    pass

            # 4) Final fallback: ASCII bell
            print('\a', end='', flush=True)
        except Exception as e:
            logger.error(f"Audio alert failed: {e}")

    def _handle_log_trigger(self, trigger_event) -> None:
        """Handle log-to-file action for trigger."""
        try:
            with open("uartium_triggers.log", "a") as f:
                timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(trigger_event.timestamp))
                f.write(f"{timestamp_str} - {trigger_event.trigger_name}: {trigger_event.message}\n")
        except Exception as e:
            logger.error(f"Failed to log trigger: {e}")
