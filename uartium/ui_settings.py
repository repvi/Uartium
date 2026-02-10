"""UI builder for the settings window."""

import dearpygui.dearpygui as dpg


def build_settings_window(app) -> None:
    """Build the modal settings window."""
    with dpg.window(
        label="[SETTINGS] Application Configuration",
        tag="settings_window",
        show=False,
        width=480,
        height=400,
        pos=(280, 100),
        modal=True,
        no_resize=True,
    ):
        dpg.add_spacer(height=8)
        dpg.add_text("[APPEARANCE] Theme Selection", color=(139, 233, 253, 255))
        dpg.add_spacer(height=12)

        with dpg.child_window(height=120, border=True):
            dpg.add_spacer(height=6)
            dpg.add_radio_button(
                ["[DARK] Modern Dark Theme", "[LIGHT] Clean Light Theme"],
                default_value=(
                    "[DARK] Modern Dark Theme"
                    if app._current_theme == "dark"
                    else "[LIGHT] Clean Light Theme"
                ),
                callback=app._on_theme_changed,
                tag="theme_selector",
            )
            dpg.add_spacer(height=6)

        dpg.add_spacer(height=20)
        dpg.add_text("[SYSTEM] Status", color=(139, 233, 253, 255))
        dpg.add_spacer(height=8)
        dpg.add_text(
            "Status: Configured | Version: 1.0 Enterprise",
            color=(180, 200, 210, 255),
        )
        dpg.add_spacer(height=20)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=50)
            dpg.add_button(
                label="[SAVE] Save Configuration",
                callback=app._save_settings,
                width=190,
                height=35,
            )
            dpg.add_spacer(width=10)
            dpg.add_button(
                label="[EXIT] Close",
                callback=lambda: dpg.hide_item("settings_window"),
                width=130,
                height=35,
            )
