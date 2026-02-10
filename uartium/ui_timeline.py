"""UI builder for the timeline graph and tooltip."""

import dearpygui.dearpygui as dpg


def build_timeline_panel(app, level_y: dict, level_plot_colors: dict) -> None:
    """Build the right column timeline panel and plot."""
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
                default_value=app._level_filters["INFO"],
                callback=app._on_filter_changed,
                user_data="INFO",
                tag="filter_INFO",
            )
            dpg.add_spacer(width=1)
            dpg.add_checkbox(
                label="WARN",
                default_value=app._level_filters["WARNING"],
                callback=app._on_filter_changed,
                user_data="WARNING",
                tag="filter_WARNING",
            )
            dpg.add_spacer(width=1)
            dpg.add_checkbox(
                label="ERROR",
                default_value=app._level_filters["ERROR"],
                callback=app._on_filter_changed,
                user_data="ERROR",
                tag="filter_ERROR",
            )
            dpg.add_spacer(width=1)
            dpg.add_checkbox(
                label="DEBUG",
                default_value=app._level_filters["DEBUG"],
                callback=app._on_filter_changed,
                user_data="DEBUG",
                tag="filter_DEBUG",
            )

        dpg.add_spacer(height=6)
        with dpg.plot(label="##timeline", height=-20, width=-20, tag="timeline_plot"):
            app._x_axis_tag = dpg.add_plot_axis(dpg.mvXAxis, label="Time (s)")
            with dpg.plot_axis(dpg.mvYAxis, label="Level", tag="timeline_y_axis"):
                dpg.set_axis_limits("timeline_y_axis", 0.0, 5.0)
                # one scatter series per level
                for lvl in level_y:
                    col255 = tuple(int(c * 255) for c in level_plot_colors[lvl])
                    series_tag = dpg.add_scatter_series([], [], label=lvl)
                    app._plot_series[lvl] = series_tag

                    # per-series colour theme
                    with dpg.theme() as s_theme:
                        with dpg.theme_component(dpg.mvScatterSeries):
                            dpg.add_theme_color(
                                dpg.mvPlotCol_MarkerFill,
                                col255,
                                category=dpg.mvThemeCat_Plots,
                            )
                            dpg.add_theme_color(
                                dpg.mvPlotCol_MarkerOutline,
                                col255,
                                category=dpg.mvThemeCat_Plots,
                            )
                            dpg.add_theme_style(
                                dpg.mvPlotStyleVar_MarkerSize,
                                5,
                                category=dpg.mvThemeCat_Plots,
                            )
                    dpg.bind_item_theme(series_tag, s_theme)


def build_timeline_tooltip(app) -> None:
    """Build the hover tooltip window for the timeline plot."""
    with dpg.window(
        tag=app._timeline_tooltip_window,
        show=False,
        no_title_bar=True,
        no_resize=True,
        no_move=True,
        no_background=False,
        no_scrollbar=False,
        no_collapse=True,
        no_saved_settings=True,
        no_focus_on_appearing=True,
        autosize=False,
        width=120,
        height=150,
    ):
        dpg.add_text("", tag=app._timeline_tooltip_header, color=(139, 233, 253, 255), wrap=110)
        dpg.add_text("", tag=app._timeline_tooltip_body, color=(220, 220, 230, 255), wrap=110)

    # Tooltip theme: semi-transparent background and tighter padding
    with dpg.theme() as _tooltip_theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (24, 24, 32, 128))
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 8, 6)
    dpg.bind_item_theme(app._timeline_tooltip_window, _tooltip_theme)
