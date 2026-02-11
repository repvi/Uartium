"""UI builder for the statistics window."""

import dearpygui.dearpygui as dpg

from uartium.ui_tags import TAG_STATS_WINDOW


def build_stats_window(app, level_colors: dict) -> None:
    """Build the statistics popup window."""
    with dpg.window(
        label="Session Statistics",
        tag=TAG_STATS_WINDOW,
        show=False,
        width=600,
        height=500,
        pos=[300, 150],
        modal=False,
        on_close=lambda: dpg.hide_item(TAG_STATS_WINDOW)
    ):
        dpg.add_text("📊 SESSION STATISTICS", color=(139, 233, 253, 255))
        dpg.add_separator()
        dpg.add_spacer(height=12)

        # Message count cards in a 2x2 grid (no nested scrolling)
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)

            # Left column
            with dpg.group():
                _build_stat_card(
                    app,
                    "INFO Messages",
                    level_colors["INFO"],
                    lambda: app._stat_info,
                    setter=lambda t: setattr(app, '_stat_info', t),
                    width=250
                )
                dpg.add_spacer(height=16)
                _build_stat_card(
                    app,
                    "ERROR Messages",
                    level_colors["ERROR"],
                    lambda: app._stat_error,
                    setter=lambda t: setattr(app, '_stat_error', t),
                    width=250
                )

            dpg.add_spacer(width=20)

            # Right column
            with dpg.group():
                _build_stat_card(
                    app,
                    "WARNING Messages",
                    level_colors["WARNING"],
                    lambda: app._stat_warn,
                    setter=lambda t: setattr(app, '_stat_warn', t),
                    width=250
                )
                dpg.add_spacer(height=16)
                _build_stat_card(
                    app,
                    "DEBUG Messages",
                    level_colors["DEBUG"],
                    lambda: app._stat_debug,
                    setter=lambda t: setattr(app, '_stat_debug', t),
                    width=250
                )

        dpg.add_spacer(height=20)
        dpg.add_separator()
        dpg.add_spacer(height=12)

        # Performance metrics section (simple text, no scrolling container)
        dpg.add_text("Performance Metrics", color=(139, 233, 253, 255))
        dpg.add_spacer(height=8)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            with dpg.group():
                app._stat_rate = dpg.add_text(
                    "Rate: 0.0 msg/sec",
                    color=(189, 147, 249, 255),
                )
                dpg.add_spacer(height=4)
                app._stat_total = dpg.add_text(
                    "Total Messages: 0",
                    color=(100, 210, 255, 255),
                )
                dpg.add_spacer(height=4)
                app._stat_errors_total = dpg.add_text(
                    "Total Errors: 0",
                    color=(255, 121, 198, 255),
                )
                dpg.add_spacer(height=4)
                app._stat_session_time = dpg.add_text(
                    "Session Duration: 00:00:00",
                    color=(139, 233, 253, 255),
                )


def _build_stat_card(app, label: str, color: tuple, getter, setter, width: int = 110) -> None:
    """Build a statistics card for a message level (no scrolling)."""
    # Card with border - using group and themed elements instead of child_window
    with dpg.group():
        # Bordered container using table for clean borders
        with dpg.table(
            header_row=False,
            borders_outerH=True,
            borders_outerV=True,
            borders_innerH=False,
            borders_innerV=False,
            policy=dpg.mvTable_SizingFixedFit
        ):
            dpg.add_table_column(init_width_or_weight=width)

            with dpg.table_row():
                with dpg.table_cell():
                    dpg.add_spacer(height=8)
                    # Label at top
                    dpg.add_text(label, color=(200, 200, 210, 255))

                    dpg.add_spacer(height=6)

                    # Count value (larger, colored)
                    text_tag = dpg.add_text("0", color=color)
                    setter(text_tag)

                    dpg.add_spacer(height=8)
