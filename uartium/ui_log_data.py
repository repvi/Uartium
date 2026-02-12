"""UI builder for the message log and data monitor."""

import dearpygui.dearpygui as dpg

from uartium import colors
from uartium.ui_tags import TAG_DATA_MONITOR_WINDOW, TAG_DATA_TABLE, TAG_LOG_WINDOW


def build_log_and_data(app) -> None:
    """Build the left column with the log window and data monitor."""
    # LEFT COLUMN: Message log and data monitor
    with dpg.child_window(width=700, border=False):
        # Message Log
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=8)
            dpg.add_text("MESSAGE LOG", color=colors.UI_HEADER_CYAN)
        dpg.add_spacer(height=4)
        app._log_parent = dpg.add_child_window(height=360, border=True, tag=TAG_LOG_WINDOW)

        # Apply compact spacing to log window
        with dpg.theme() as log_compact_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 0, 3)
        dpg.bind_item_theme(TAG_LOG_WINDOW, log_compact_theme)

        dpg.add_spacer(height=8)

        # Data Monitor
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=8)
            dpg.add_text("DATA MONITOR", color=colors.UI_HEADER_CYAN)
        dpg.add_spacer(height=4)
        with dpg.child_window(height=160, border=True, tag=TAG_DATA_MONITOR_WINDOW):
            with dpg.table(
                tag=TAG_DATA_TABLE,
                header_row=True,
                borders_innerH=True,
                borders_innerV=True,
                borders_outerH=True,
                borders_outerV=True,
                resizable=True,
                policy=dpg.mvTable_SizingStretchProp,
            ):
                dpg.add_table_column(label="Variable", width_fixed=True, init_width_or_weight=200)
                dpg.add_table_column(label="Type", width_fixed=True, init_width_or_weight=80)
                dpg.add_table_column(label="Value")
