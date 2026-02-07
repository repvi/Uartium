"""
Uartium - Dear PyGui GUI
=========================

Main GUI window with:
  - Start / Stop buttons
  - Scrollable, colour-coded message log
  - Real-time timeline chart of message levels
"""

from __future__ import annotations

import time
from collections import deque
from typing import Optional

import dearpygui.dearpygui as dpg

from uartium.serial_backend import DemoSerialBackend, SerialBackend

# ---------------------------------------------------------------------------
# Colour palette  (R, G, B, A  — 0-255)
# ---------------------------------------------------------------------------
LEVEL_COLORS: dict[str, tuple[int, int, int, int]] = {
    "EVENT":   (100, 220, 100, 255),   # green
    "INFO":    (180, 210, 255, 255),   # light blue
    "WARNING": (255, 200,  60, 255),   # amber / yellow
    "ERROR":   (255,  80,  80, 255),   # red
    "DEBUG":   (170, 170, 170, 255),   # grey
}

LEVEL_BADGE: dict[str, str] = {
    "EVENT":   "[EVENT]  ",
    "INFO":    "[INFO]   ",
    "WARNING": "[WARN]   ",
    "ERROR":   "[ERROR]  ",
    "DEBUG":   "[DEBUG]  ",
}

# Numeric ID for the timeline Y-axis (so the chart is categorical-ish)
LEVEL_Y: dict[str, float] = {
    "DEBUG":   1.0,
    "INFO":    2.0,
    "EVENT":   3.0,
    "WARNING": 4.0,
    "ERROR":   5.0,
}

# matching scatter colours per level  (normalised 0-1 for plot themes)
LEVEL_PLOT_COLORS: dict[str, tuple[float, float, float, float]] = {
    "EVENT":   (0.39, 0.86, 0.39, 1.0),
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


class UartiumApp:
    """Encapsulates the entire Dear PyGui application."""

    def __init__(self, backend=None):
        self.backend = backend or DemoSerialBackend(interval=0.5)
        self._start_time: Optional[float] = None

        # per-level timeline data
        self._timeline_x: dict[str, deque] = {lvl: deque(maxlen=MAX_TIMELINE_POINTS) for lvl in LEVEL_Y}
        self._timeline_y: dict[str, deque] = {lvl: deque(maxlen=MAX_TIMELINE_POINTS) for lvl in LEVEL_Y}

        # dpg tag references (assigned during build)
        self._log_parent: int | str = 0
        self._status_text: int | str = 0
        self._msg_count = 0
        self._plot_series: dict[str, int | str] = {}
        self._x_axis_tag: int | str = 0

    # -- build UI -----------------------------------------------------------
    def build(self) -> None:
        dpg.create_context()

        # ---- global theme / font ----
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 12, 12)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 6)
                dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (30, 30, 38, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (20, 20, 28, 255))
                dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, (45, 45, 60, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (22, 22, 30, 255))
        dpg.bind_theme(global_theme)

        # ---- main viewport window ----
        with dpg.window(tag="primary_window"):
            # -- toolbar row --
            with dpg.group(horizontal=True):
                dpg.add_button(label="  Start  ", tag="btn_start", callback=self._on_start)
                dpg.add_button(label="  Stop  ",  tag="btn_stop",  callback=self._on_stop, enabled=False)
                dpg.add_spacer(width=20)
                self._status_text = dpg.add_text("Status: Stopped", color=(180, 180, 180, 255))

            dpg.add_separator()
            dpg.add_spacer(height=4)

            # -- colour legend --
            with dpg.group(horizontal=True):
                for lvl, col in LEVEL_COLORS.items():
                    dpg.add_text(f"  {lvl}  ", color=col)

            dpg.add_spacer(height=4)

            # -- scrolling message log --
            dpg.add_text("Message Log", color=(220, 220, 220, 255))
            self._log_parent = dpg.add_child_window(height=320, border=True, tag="log_window")

            dpg.add_spacer(height=8)

            # -- timeline chart --
            dpg.add_text("Event Timeline", color=(220, 220, 220, 255))
            with dpg.plot(label="##timeline", height=220, width=-1, tag="timeline_plot"):
                self._x_axis_tag = dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)")
                with dpg.plot_axis(dpg.mvYAxis, label="Level", tag="timeline_y_axis"):
                    dpg.set_axis_limits("timeline_y_axis", 0.0, 6.0)
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

        # ---- button themes ----
        with dpg.theme() as start_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (40, 120, 40, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (55, 155, 55, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (30, 100, 30, 255))
        dpg.bind_item_theme("btn_start", start_theme)

        with dpg.theme() as stop_theme:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (150, 40, 40, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (190, 55, 55, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (120, 30, 30, 255))
        dpg.bind_item_theme("btn_stop", stop_theme)

    # -- run loop -----------------------------------------------------------
    def run(self) -> None:
        dpg.create_viewport(title="Uartium — UART Monitor", width=960, height=700)
        dpg.setup_dearpygui()
        dpg.set_primary_window("primary_window", True)
        dpg.show_viewport()

        # main render loop with message polling
        while dpg.is_dearpygui_running():
            self._poll_messages()
            dpg.render_dearpygui_frame()

        # cleanup
        self.backend.stop()
        dpg.destroy_context()

    # -- callbacks ----------------------------------------------------------
    def _on_start(self) -> None:
        self.backend.start()
        self._start_time = time.time()
        dpg.configure_item("btn_start", enabled=False)
        dpg.configure_item("btn_stop", enabled=True)
        dpg.set_value(self._status_text, "Status: Running")
        dpg.configure_item(self._status_text, color=(100, 220, 100, 255))

    def _on_stop(self) -> None:
        self.backend.stop()
        dpg.configure_item("btn_start", enabled=True)
        dpg.configure_item("btn_stop", enabled=False)
        dpg.set_value(self._status_text, "Status: Stopped")
        dpg.configure_item(self._status_text, color=(180, 180, 180, 255))

    # -- message pump -------------------------------------------------------
    def _poll_messages(self) -> None:
        """Drain all pending messages from the backend into the GUI."""
        batch = 0
        while batch < 50:  # cap per frame to stay responsive
            msg = self.backend.read_message()
            if msg is None:
                break
            self._add_log_line(msg)
            self._add_timeline_point(msg)
            batch += 1

    def _add_log_line(self, msg: dict) -> None:
        level = msg["level"]
        color = LEVEL_COLORS.get(level, (200, 200, 200, 255))
        badge = LEVEL_BADGE.get(level, "[???]    ")
        ts = time.strftime("%H:%M:%S", time.localtime(msg["timestamp"]))
        line = f"{ts}  {badge}{msg['text']}"

        self._msg_count += 1

        # trim oldest lines to keep memory bounded
        if self._msg_count > MAX_LOG_LINES:
            children = dpg.get_item_children(self._log_parent, slot=1)
            if children:
                dpg.delete_item(children[0])

        dpg.add_text(line, parent=self._log_parent, color=color)

        # auto-scroll to bottom
        dpg.set_y_scroll(self._log_parent, dpg.get_y_scroll_max(self._log_parent) + 100)

    def _add_timeline_point(self, msg: dict) -> None:
        level = msg["level"]
        if self._start_time is None:
            return
        elapsed = msg["timestamp"] - self._start_time
        y = LEVEL_Y.get(level, 2.0)

        self._timeline_x[level].append(elapsed)
        self._timeline_y[level].append(y)

        # update the scatter series data
        series_tag = self._plot_series.get(level)
        if series_tag:
            dpg.set_value(series_tag, [list(self._timeline_x[level]),
                                        list(self._timeline_y[level])])

        # auto-fit x-axis
        dpg.fit_axis_data(self._x_axis_tag)
