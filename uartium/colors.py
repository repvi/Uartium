"""
Uartium Color Palette
=====================

Centralized color definitions for the Uartium UI.
All colors are in RGBA format (R, G, B, A) with values 0-255.
"""

# ---------------------------------------------------------------------------
# Log Level Colors (RGBA 0-255)
# ---------------------------------------------------------------------------
ELECTRIC_CYAN_BLUE = (100, 210, 255, 255)    # INFO level
VIBRANT_AMBER = (255, 193, 7, 255)           # WARNING level
HOT_RED = (255, 82, 82, 255)                 # ERROR level
SOFT_PURPLE = (189, 147, 249, 255)           # DEBUG level
NEUTRAL_GREY = (200, 200, 200, 255)          # Fallback color

LEVEL_COLORS = {
    "INFO": ELECTRIC_CYAN_BLUE,
    "WARNING": VIBRANT_AMBER,
    "ERROR": HOT_RED,
    "DEBUG": SOFT_PURPLE,
}

# ---------------------------------------------------------------------------
# Dark Theme Colors (Modern Midnight Blue)
# ---------------------------------------------------------------------------
DARK_DEEP_MIDNIGHT = (18, 18, 24, 255)       # Window background
DARK_RICH_BLUE = (24, 24, 32, 255)           # Child background
DARK_BLUE_GREY = (28, 28, 38, 255)           # Title background
DARK_SLATE_BLUE = (40, 42, 54, 255)          # Active title background
DARK_MODERN_GREY_BLUE = (68, 71, 90, 255)    # Button default
DARK_PERIWINKLE_BLUE = (98, 114, 164, 255)   # Button hovered
DARK_BRIGHT_GREEN = (80, 250, 123, 255)      # Button active / Success
DARK_SLATE = (44, 47, 62, 255)               # Header
DARK_LIGHT_SLATE = (68, 71, 90, 255)         # Header hovered
DARK_SOFT_WHITE = (248, 248, 242, 255)       # Text
DARK_SUBTLE_BORDER = (68, 71, 90, 200)       # Border (with transparency)
DARK_FRAME_BG = (30, 30, 40, 255)            # Frame background
DARK_FRAME_HOVERED = (40, 42, 54, 255)       # Frame hovered
DARK_CYAN_ACCENT = (139, 233, 253, 255)      # Accent color
DARK_ACCENT_DIM = (98, 114, 164, 255)        # Dimmed accent

DARK_THEME = {
    "window_bg": DARK_DEEP_MIDNIGHT,
    "child_bg": DARK_RICH_BLUE,
    "title_bg": DARK_BLUE_GREY,
    "title_bg_active": DARK_SLATE_BLUE,
    "button": DARK_MODERN_GREY_BLUE,
    "button_hovered": DARK_PERIWINKLE_BLUE,
    "button_active": DARK_BRIGHT_GREEN,
    "header": DARK_SLATE,
    "header_hovered": DARK_LIGHT_SLATE,
    "text": DARK_SOFT_WHITE,
    "border": DARK_SUBTLE_BORDER,
    "frame_bg": DARK_FRAME_BG,
    "frame_bg_hovered": DARK_FRAME_HOVERED,
    "accent": DARK_CYAN_ACCENT,
    "accent_dim": DARK_ACCENT_DIM,
    "success": DARK_BRIGHT_GREEN,
    "warning": VIBRANT_AMBER,
    "error": HOT_RED,
}

# ---------------------------------------------------------------------------
# Light Theme Colors (Clean & Bright)
# ---------------------------------------------------------------------------
LIGHT_OFF_WHITE = (248, 249, 250, 255)       # Window background
LIGHT_PURE_WHITE = (255, 255, 255, 255)      # Child background
LIGHT_LIGHT_GREY = (233, 236, 239, 255)      # Title background / Button
LIGHT_MEDIUM_GREY = (206, 212, 218, 255)     # Active title background
LIGHT_BRIGHT_BLUE = (13, 110, 253, 255)      # Button hovered / Accent
LIGHT_DEEP_BLUE = (10, 88, 202, 255)         # Button active
LIGHT_PALE_GREY = (241, 243, 245, 255)       # Header
LIGHT_MED_GREY = (222, 226, 230, 255)        # Header hovered
LIGHT_DARK_TEXT = (33, 37, 41, 255)          # Text
LIGHT_SUBTLE_BORDER = (206, 212, 218, 180)   # Border (with transparency)
LIGHT_FRAME_BG = (248, 249, 250, 255)        # Frame background
LIGHT_FRAME_HOVERED = (233, 236, 239, 255)   # Frame hovered
LIGHT_ACCENT_DIM = (108, 117, 125, 255)      # Dimmed accent
LIGHT_SUCCESS_GREEN = (25, 135, 84, 255)     # Success

LIGHT_THEME = {
    "window_bg": LIGHT_OFF_WHITE,
    "child_bg": LIGHT_PURE_WHITE,
    "title_bg": LIGHT_LIGHT_GREY,
    "title_bg_active": LIGHT_MEDIUM_GREY,
    "button": LIGHT_LIGHT_GREY,
    "button_hovered": LIGHT_BRIGHT_BLUE,
    "button_active": LIGHT_DEEP_BLUE,
    "header": LIGHT_PALE_GREY,
    "header_hovered": LIGHT_MED_GREY,
    "text": LIGHT_DARK_TEXT,
    "border": LIGHT_SUBTLE_BORDER,
    "frame_bg": LIGHT_FRAME_BG,
    "frame_bg_hovered": LIGHT_FRAME_HOVERED,
    "accent": LIGHT_BRIGHT_BLUE,
    "accent_dim": LIGHT_ACCENT_DIM,
    "success": LIGHT_SUCCESS_GREEN,
    "warning": VIBRANT_AMBER,
    "error": HOT_RED,
}

# ---------------------------------------------------------------------------
# Button-Specific Colors
# ---------------------------------------------------------------------------
# Start Button (Modern Green)
START_BUTTON_DEFAULT = (46, 160, 67, 255)
START_BUTTON_HOVERED = (72, 187, 120, 255)
START_BUTTON_ACTIVE = (34, 139, 34, 255)
START_BUTTON_TEXT = (255, 255, 255, 255)

# Stop Button (Modern Red)
STOP_BUTTON_DEFAULT = (220, 53, 69, 255)
STOP_BUTTON_HOVERED = (248, 81, 73, 255)
STOP_BUTTON_ACTIVE = (176, 42, 55, 255)
STOP_BUTTON_TEXT = (255, 255, 255, 255)

# Utility Buttons (Grey-Blue)
UTILITY_BUTTON_DEFAULT = (68, 71, 90, 255)
UTILITY_BUTTON_HOVERED = (98, 114, 164, 255)
UTILITY_BUTTON_ACTIVE = (80, 250, 123, 255)

# ---------------------------------------------------------------------------
# Status Text Colors
# ---------------------------------------------------------------------------
STATUS_STOPPED = (180, 180, 180, 255)        # Grey when stopped
STATUS_RUNNING = (80, 250, 123, 255)         # Green when running
STATUS_SUCCESS = (80, 250, 123, 255)         # Green for success messages
STATUS_INFO = (139, 233, 253, 255)           # Cyan for info messages
STATUS_WARNING = (255, 193, 7, 255)          # Amber for warnings
STATUS_ERROR = (255, 82, 82, 255)            # Red for errors

# ---------------------------------------------------------------------------
# Plot Colors (Normalized 0-1 for DearPyGui plots)
# ---------------------------------------------------------------------------
PLOT_INFO_CYAN = (0.71, 0.82, 1.00, 1.0)
PLOT_WARNING_AMBER = (1.00, 0.78, 0.24, 1.0)
PLOT_ERROR_RED = (1.00, 0.31, 0.31, 1.0)
PLOT_DEBUG_GREY = (0.67, 0.67, 0.67, 1.0)

LEVEL_PLOT_COLORS = {
    "INFO": PLOT_INFO_CYAN,
    "WARNING": PLOT_WARNING_AMBER,
    "ERROR": PLOT_ERROR_RED,
    "DEBUG": PLOT_DEBUG_GREY,
}

# ---------------------------------------------------------------------------
# Transparency Helpers
# ---------------------------------------------------------------------------
TRANSPARENT = (0, 0, 0, 0)                   # Fully transparent
WHITE = (255, 255, 255, 255)                 # Pure white
BLACK = (0, 0, 0, 255)                       # Pure black

# ---------------------------------------------------------------------------
# UI Component Colors
# ---------------------------------------------------------------------------
# Headers and Titles
UI_HEADER_CYAN = (139, 233, 253, 255)        # Main header color (cyan accent)
UI_LABEL_GREY = (200, 200, 210, 255)         # Standard label color
UI_LABEL_DIM = (180, 180, 190, 255)          # Dimmed label color
UI_PLACEHOLDER = (128, 128, 128, 255)        # Placeholder text
UI_TEXT_LIGHT = (200, 200, 200, 255)         # Light text color
UI_TEXT_DIM = (150, 150, 150, 255)           # Dim text color
UI_TEXT_NORMAL = (220, 220, 230, 255)        # Normal text color
UI_TEXT_STATUS = (180, 200, 210, 255)        # Status text color
UI_UPTIME = (150, 150, 160, 255)             # Uptime text color
UI_READY = (180, 180, 180, 255)              # Ready state color

# Metric/Stat Colors
STAT_RATE_PURPLE = (189, 147, 249, 255)      # Rate metric color
STAT_TOTAL_CYAN = (100, 210, 255, 255)       # Total messages color
STAT_ERROR_PINK = (255, 121, 198, 255)       # Error count color
STAT_TIME_CYAN = (139, 233, 253, 255)        # Time/duration color

# Trigger Colors
TRIGGER_ENABLED = (80, 250, 123, 255)        # Enabled trigger
TRIGGER_DISABLED = (128, 128, 128, 255)      # Disabled trigger
TRIGGER_FIRED = (255, 193, 7, 255)           # Trigger fired (warning amber)

# Graph Line Colors (for cycling through variables)
GRAPH_LINE_COLORS = [
    (100, 210, 255, 255),   # Cyan
    (80, 250, 123, 255),    # Green
    (255, 193, 7, 255),     # Amber
    (255, 121, 198, 255),   # Pink
    (189, 147, 249, 255),   # Purple
    (139, 233, 253, 255),   # Light cyan
    (255, 184, 108, 255),   # Orange
    (80, 250, 210, 255),    # Turquoise
]

# Tooltip Colors
TOOLTIP_BG = (24, 24, 32, 128)               # Semi-transparent tooltip background
TOOLTIP_HEADER = (139, 233, 253, 255)        # Tooltip header color
TOOLTIP_BODY = (220, 220, 230, 255)          # Tooltip body text
