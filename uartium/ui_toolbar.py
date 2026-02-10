"""UI builder for the top toolbar and status row."""

import dearpygui.dearpygui as dpg

from uartium.ui_tags import (
    TAG_BAUD_COMBO,
    TAG_BTN_EXPORT_CSV,
    TAG_BTN_SETTINGS,
    TAG_BTN_START,
    TAG_BTN_STOP,
    TAG_BTN_TOGGLE_STATS,
    TAG_MODE_RADIO,
    TAG_PORT_INPUT,
    TAG_SETTINGS_WINDOW,
    TAG_STATUS_ROW,
    TAG_TOOLBAR_PANEL,
)


def build_toolbar(app) -> None:
    """Build the top toolbar and status row."""
    # Use a non-scrolling group container for the toolbar to avoid scroll behavior
    with dpg.group(tag=TAG_TOOLBAR_PANEL):
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            # Main control buttons
            dpg.add_button(
                label="START",
                tag=TAG_BTN_START,
                callback=app._on_start,
                width=100,
                height=38,
            )
            dpg.add_button(
                label="STOP",
                tag=TAG_BTN_STOP,
                callback=app._on_stop,
                enabled=False,
                width=100,
                height=38,
            )

            # Port configuration group
            with dpg.group(horizontal=True):
                dpg.add_text("Port:", color=(200, 200, 210, 255))
                dpg.add_input_text(default_value="COM3", width=90, tag=TAG_PORT_INPUT)
                dpg.add_text("Baud:", color=(200, 200, 210, 255))
                app._baud_input = dpg.add_combo(
                    items=[
                        "9600",
                        "19200",
                        "38400",
                        "57600",
                        "115200",
                        "230400",
                        "460800",
                        "921600",
                    ],
                    default_value=str(app._initial_baudrate),
                    width=100,
                    tag=TAG_BAUD_COMBO,
                    callback=app._on_baud_changed,
                )

            # Mode selector
            with dpg.group(horizontal=True):
                dpg.add_text("Mode:", color=(200, 200, 210, 255))
                dpg.add_radio_button(
                    ["Demo", "Real Serial"],
                    default_value="Demo" if app._use_demo else "Real Serial",
                    horizontal=True,
                    callback=app._on_mode_changed,
                    tag=TAG_MODE_RADIO,
                )

            # Utility buttons
            dpg.add_button(
                label="Statistics",
                tag=TAG_BTN_TOGGLE_STATS,
                callback=app._toggle_statistics,
                width=90,
                height=28,
            )
            dpg.add_button(
                label="Export CSV",
                tag=TAG_BTN_EXPORT_CSV,
                callback=app._export_to_csv,
                width=90,
                height=28,
            )
            dpg.add_button(
                label="Help",
                tag=TAG_BTN_SETTINGS,
                callback=lambda: dpg.show_item(TAG_SETTINGS_WINDOW),
                width=70,
                height=28,
            )
            dpg.add_spacer(width=20)

        # Status row below the toolbar controls (indented)
        dpg.add_spacer(height=2)
        with dpg.group(horizontal=True, tag=TAG_STATUS_ROW):
            dpg.add_spacer(width=18)
            app._status_text = dpg.add_text("Ready", color=(180, 180, 180, 255))
            dpg.add_spacer(width=10)
            app._status_uptime = dpg.add_text("Uptime: 00:00:00", color=(150, 150, 160, 255))
