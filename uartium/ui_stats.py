"""UI builder for the statistics panel."""

import dearpygui.dearpygui as dpg


def build_stats_panel(app, level_colors: dict) -> None:
    """Build the statistics panel."""
    with dpg.child_window(
        height=72,
        border=True,
        tag="stats_panel",
        show=app._stats_visible,
        no_scrollbar=True,
    ):
        dpg.add_spacer(height=6)
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=12)
            dpg.add_text("STATISTICS", color=(139, 233, 253, 255))
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=16)
            with dpg.group():
                with dpg.group(horizontal=True):
                    app._stat_info = dpg.add_text("INFO: 0", color=level_colors["INFO"])
                    dpg.add_spacer(width=20)
                    app._stat_warn = dpg.add_text("WARN: 0", color=level_colors["WARNING"])
                    dpg.add_spacer(width=20)
                    app._stat_error = dpg.add_text("ERROR: 0", color=level_colors["ERROR"])
                    dpg.add_spacer(width=20)
                    app._stat_debug = dpg.add_text("DEBUG: 0", color=level_colors["DEBUG"])
                dpg.add_spacer(height=4)
                app._stat_rate = dpg.add_text(
                    "Rate: 0.0 msg/sec | Total: 0 msgs | Errors: 0",
                    color=(189, 147, 249, 255),
                )
