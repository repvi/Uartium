"""
Uartium - Real-Time Variable Graphing Module
=============================================

Provides professional real-time line graphs for numeric variables:
  - Multi-line chart showing numeric variables over time
  - Pin/unpin specific variables to graph
  - Auto-scale and manual zoom controls
  - Color-coded lines for easy identification
  - Synchronized with message timeline
"""

from __future__ import annotations
from collections import deque
from typing import TYPE_CHECKING
import dearpygui.dearpygui as dpg

if TYPE_CHECKING:
    from uartium.gui import UartiumApp

# Maximum data points to keep per variable
MAX_GRAPH_POINTS = 1000

# Color palette for graph lines (cycle through these colors)
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


def build_graph_panel(app: UartiumApp) -> None:
    """
    Build the real-time variable graphing panel.

    Creates a panel with:
    - Line graph showing pinned numeric variables over time
    - Variable selector (checkboxes to pin/unpin variables)
    - Auto-scale and fit controls
    - Clear graph button
    """
    # Initialize graph state in app if not exists
    if not hasattr(app, '_graph_data'):
        app._graph_data = {}  # var_name -> {"x": deque, "y": deque, "type": str}
    if not hasattr(app, '_pinned_vars'):
        app._pinned_vars = set()  # set of pinned variable names
    if not hasattr(app, '_graph_series'):
        app._graph_series = {}  # var_name -> series_tag
    if not hasattr(app, '_graph_checkboxes'):
        app._graph_checkboxes = {}  # var_name -> checkbox_tag
    if not hasattr(app, '_graph_color_index'):
        app._graph_color_index = 0

    with dpg.child_window(
        label="Real-Time Variable Graphs",
        width=450,
        height=-1,
        border=True,
        tag="graph_panel"
    ):
        dpg.add_text("Real-Time Variable Graphs", color=(139, 233, 253, 255))
        dpg.add_separator()
        dpg.add_spacer(height=4)

        # Control buttons
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="Clear All",
                callback=lambda: _clear_all_graphs(app),
                width=100,
                tag="btn_clear_graphs"
            )
            dpg.add_button(
                label="Auto Fit",
                callback=lambda: _auto_fit_graph(app),
                width=100,
                tag="btn_fit_graph"
            )
            dpg.add_button(
                label="Unpin All",
                callback=lambda: _unpin_all_variables(app),
                width=100,
                tag="btn_unpin_all"
            )

        dpg.add_spacer(height=8)

        # Graph plot
        with dpg.plot(
            label="Variable Trends",
            height=300,
            width=-1,
            tag="var_graph_plot",
            anti_aliased=True
        ):
            dpg.add_plot_legend(location=dpg.mvPlot_Location_NorthEast)
            app._graph_x_axis = dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)", tag="graph_x_axis")
            app._graph_y_axis = dpg.add_plot_axis(dpg.mvYAxis, label="Value", tag="graph_y_axis")
            # Series will be added dynamically as variables are pinned

        dpg.add_spacer(height=8)
        dpg.add_separator()
        dpg.add_spacer(height=4)

        # Variable selector section
        dpg.add_text("Available Variables (check to graph)", color=(200, 200, 200, 255))
        dpg.add_spacer(height=4)

        # Scrollable area for variable checkboxes
        with dpg.child_window(
            height=200,
            border=True,
            tag="var_selector_window"
        ):
            dpg.add_text("(Numeric variables will appear here)", color=(128, 128, 128, 255), tag="var_placeholder")


def update_graph_data(app: UartiumApp, var_name: str, value: float, timestamp: float, var_type: str) -> None:
    """
    Update graph data for a specific variable.

    Args:
        app: The main application instance
        var_name: Variable name
        value: Numeric value
        timestamp: Timestamp (relative to session start)
        var_type: Variable type (uint, int, float, timestamp)
    """
    # Only graph numeric types
    if var_type not in ("uint", "int", "float", "timestamp"):
        return

    # Initialize graph data structures if first call
    if not hasattr(app, '_graph_data'):
        app._graph_data = {}
        app._pinned_vars = set()
        app._graph_series = {}
        app._graph_checkboxes = {}
        app._graph_color_index = 0

    # Initialize data for this variable if first time seeing it
    if var_name not in app._graph_data:
        app._graph_data[var_name] = {
            "x": deque(maxlen=MAX_GRAPH_POINTS),
            "y": deque(maxlen=MAX_GRAPH_POINTS),
            "type": var_type
        }

        # Add checkbox for this variable in the selector
        _add_variable_checkbox(app, var_name)

    # Append data point
    app._graph_data[var_name]["x"].append(timestamp)
    app._graph_data[var_name]["y"].append(float(value))

    # Update graph series if this variable is pinned
    if var_name in app._pinned_vars:
        _update_graph_series(app, var_name)


def _add_variable_checkbox(app: UartiumApp, var_name: str) -> None:
    """Add a checkbox for a new variable in the selector."""
    # Remove placeholder text if it exists
    if dpg.does_item_exist("var_placeholder"):
        dpg.delete_item("var_placeholder")

    # Create checkbox for this variable
    checkbox_tag = f"var_check_{var_name}"

    with dpg.group(parent="var_selector_window", horizontal=True):
        checkbox = dpg.add_checkbox(
            label=var_name,
            default_value=False,
            callback=lambda s, v: _toggle_variable_pin(app, var_name, v),
            tag=checkbox_tag
        )

    app._graph_checkboxes[var_name] = checkbox_tag


def _toggle_variable_pin(app: UartiumApp, var_name: str, is_checked: bool) -> None:
    """Toggle whether a variable is pinned to the graph."""
    if is_checked:
        # Pin the variable
        app._pinned_vars.add(var_name)
        _create_graph_series(app, var_name)
        _update_graph_series(app, var_name)
    else:
        # Unpin the variable
        app._pinned_vars.discard(var_name)
        _remove_graph_series(app, var_name)

    # Auto-fit after pinning/unpinning
    _auto_fit_graph(app)


def _create_graph_series(app: UartiumApp, var_name: str) -> None:
    """Create a new line series for a pinned variable."""
    if var_name in app._graph_series:
        return  # Already exists

    # Assign a color from the palette
    color = GRAPH_LINE_COLORS[app._graph_color_index % len(GRAPH_LINE_COLORS)]
    app._graph_color_index += 1

    # Create the line series
    series_tag = f"graph_series_{var_name}"
    with dpg.theme() as series_theme:
        with dpg.theme_component(dpg.mvLineSeries):
            dpg.add_theme_color(dpg.mvPlotCol_Line, color, category=dpg.mvThemeCat_Plots)

    series = dpg.add_line_series(
        [],
        [],
        label=var_name,
        parent="graph_y_axis",
        tag=series_tag
    )
    dpg.bind_item_theme(series, series_theme)

    app._graph_series[var_name] = series_tag


def _update_graph_series(app: UartiumApp, var_name: str) -> None:
    """Update the graph series with latest data."""
    if var_name not in app._graph_series:
        return

    series_tag = app._graph_series[var_name]
    data = app._graph_data[var_name]

    # Update the series data
    dpg.set_value(series_tag, [list(data["x"]), list(data["y"])])


def _remove_graph_series(app: UartiumApp, var_name: str) -> None:
    """Remove a line series from the graph."""
    if var_name not in app._graph_series:
        return

    series_tag = app._graph_series[var_name]
    if dpg.does_item_exist(series_tag):
        dpg.delete_item(series_tag)

    del app._graph_series[var_name]


def _clear_all_graphs(app: UartiumApp) -> None:
    """Clear all graph data (but keep variable checkboxes)."""
    # Clear data
    for var_name in app._graph_data:
        app._graph_data[var_name]["x"].clear()
        app._graph_data[var_name]["y"].clear()

        # Update series to show empty
        if var_name in app._graph_series:
            _update_graph_series(app, var_name)

    _auto_fit_graph(app)


def _auto_fit_graph(app: UartiumApp) -> None:
    """Auto-fit the graph axes to show all data."""
    if dpg.does_item_exist("graph_x_axis"):
        dpg.fit_axis_data("graph_x_axis")
    if dpg.does_item_exist("graph_y_axis"):
        dpg.fit_axis_data("graph_y_axis")


def _unpin_all_variables(app: UartiumApp) -> None:
    """Unpin all variables from the graph."""
    # Uncheck all checkboxes
    for var_name, checkbox_tag in app._graph_checkboxes.items():
        if dpg.does_item_exist(checkbox_tag):
            dpg.set_value(checkbox_tag, False)

    # Remove all series
    for var_name in list(app._pinned_vars):
        _remove_graph_series(app, var_name)

    app._pinned_vars.clear()
    _auto_fit_graph(app)
