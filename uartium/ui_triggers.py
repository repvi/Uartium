"""
Uartium - Trigger Configuration UI
===================================

Provides UI for creating, editing, and managing trigger conditions.
"""

from __future__ import annotations
from typing import TYPE_CHECKING
import uuid
import time
import dearpygui.dearpygui as dpg

from uartium.triggers import (
    TriggerCondition,
    TriggerType,
    TriggerComparison,
    TriggerAction
)

if TYPE_CHECKING:
    from uartium.gui import UartiumApp


def build_triggers_window(app: UartiumApp) -> None:
    """Build the trigger configuration window."""
    with dpg.window(
        label="Trigger Configuration",
        tag="triggers_window",
        show=False,
        width=700,
        height=600,
        pos=[200, 100],
        modal=False,
        on_close=lambda: dpg.hide_item("triggers_window")
    ):
        dpg.add_text("Automated Trigger Rules", color=(139, 233, 253, 255))
        dpg.add_separator()
        dpg.add_spacer(height=8)

        # Trigger list
        with dpg.child_window(height=300, border=True, tag="trigger_list_window"):
            dpg.add_text("(No triggers configured)", color=(128, 128, 128, 255), tag="trigger_list_placeholder")

        dpg.add_spacer(height=8)

        # Control buttons
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="Add Variable Threshold",
                callback=lambda: _show_add_trigger_dialog(app, TriggerType.VARIABLE_THRESHOLD),
                width=180
            )
            dpg.add_button(
                label="Add Message Pattern",
                callback=lambda: _show_add_trigger_dialog(app, TriggerType.MESSAGE_PATTERN),
                width=180
            )
            dpg.add_button(
                label="Add Rate Monitor",
                callback=lambda: _show_add_trigger_dialog(app, TriggerType.MESSAGE_RATE),
                width=180
            )

        dpg.add_spacer(height=4)

        with dpg.group(horizontal=True):
            dpg.add_button(
                label="Clear All Triggers",
                callback=lambda: _clear_all_triggers(app),
                width=180
            )
            dpg.add_button(
                label="Save Config",
                callback=lambda: _save_trigger_config(app),
                width=180
            )
            dpg.add_button(
                label="Load Config",
                callback=lambda: _load_trigger_config(app),
                width=180
            )

        dpg.add_spacer(height=8)
        dpg.add_separator()

        # Trigger history
        dpg.add_text("Trigger History (Recent Fires)", color=(200, 200, 200, 255))
        with dpg.child_window(height=150, border=True, tag="trigger_history_window"):
            dpg.add_text("(No triggers fired yet)", color=(128, 128, 128, 255), tag="trigger_history_placeholder")


def _show_add_trigger_dialog(app: UartiumApp, trigger_type: TriggerType) -> None:
    """Show dialog to add a new trigger."""
    dialog_tag = "add_trigger_dialog"

    # Delete existing dialog if present
    if dpg.does_item_exist(dialog_tag):
        dpg.delete_item(dialog_tag)

    with dpg.window(
        label=f"Add {trigger_type.value.replace('_', ' ').title()} Trigger",
        tag=dialog_tag,
        modal=True,
        show=True,
        width=500,
        height=400,
        pos=[300, 150],
        on_close=lambda: dpg.delete_item(dialog_tag)
    ):
        dpg.add_text("Trigger Name:")
        dpg.add_input_text(tag="trigger_name_input", default_value="New Trigger", width=-1)

        dpg.add_spacer(height=8)

        if trigger_type == TriggerType.VARIABLE_THRESHOLD:
            _build_variable_threshold_inputs(app)
        elif trigger_type == TriggerType.MESSAGE_PATTERN:
            _build_message_pattern_inputs(app)
        elif trigger_type == TriggerType.MESSAGE_RATE:
            _build_message_rate_inputs(app)

        dpg.add_spacer(height=12)
        dpg.add_separator()

        # Actions
        dpg.add_text("Actions when triggered:")
        dpg.add_checkbox(label="Visual Alert", tag="action_visual", default_value=True)
        dpg.add_checkbox(label="Audio Alert", tag="action_audio", default_value=False)
        dpg.add_checkbox(label="Log to File", tag="action_log", default_value=False)

        dpg.add_spacer(height=12)

        # Buttons
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="Create Trigger",
                callback=lambda: _create_trigger_from_dialog(app, trigger_type, dialog_tag),
                width=150
            )
            dpg.add_button(
                label="Cancel",
                callback=lambda: dpg.delete_item(dialog_tag),
                width=150
            )


def _build_variable_threshold_inputs(app: UartiumApp) -> None:
    """Build inputs for variable threshold trigger."""
    dpg.add_text("Variable Name:")
    dpg.add_input_text(tag="var_name_input", hint="e.g., temp, voltage, rpm", width=-1)

    dpg.add_spacer(height=8)
    dpg.add_text("Comparison:")
    dpg.add_combo(
        items=[">", "<", ">=", "<=", "==", "!="],
        tag="comparison_input",
        default_value=">",
        width=-1
    )

    dpg.add_spacer(height=8)
    dpg.add_text("Threshold Value:")
    dpg.add_input_float(tag="threshold_input", default_value=0.0, width=-1)


def _build_message_pattern_inputs(app: UartiumApp) -> None:
    """Build inputs for message pattern trigger."""
    dpg.add_text("Search Pattern:")
    dpg.add_input_text(tag="pattern_input", hint="e.g., error, timeout, failed", width=-1)

    dpg.add_spacer(height=8)
    dpg.add_checkbox(label="Use Regular Expression", tag="regex_checkbox", default_value=False)


def _build_message_rate_inputs(app: UartiumApp) -> None:
    """Build inputs for message rate trigger."""
    dpg.add_text("Message Rate Threshold (msg/sec):")
    dpg.add_input_float(tag="rate_threshold_input", default_value=10.0, width=-1)

    dpg.add_spacer(height=8)
    dpg.add_text("Time Window (seconds):")
    dpg.add_input_float(tag="rate_window_input", default_value=60.0, width=-1)


def _create_trigger_from_dialog(app: UartiumApp, trigger_type: TriggerType, dialog_tag: str) -> None:
    """Create trigger from dialog inputs."""
    name = dpg.get_value("trigger_name_input")
    trigger_id = str(uuid.uuid4())

    # Collect actions
    actions = []
    if dpg.get_value("action_visual"):
        actions.append(TriggerAction.VISUAL_ALERT)
    if dpg.get_value("action_audio"):
        actions.append(TriggerAction.AUDIO_ALERT)
    if dpg.get_value("action_log"):
        actions.append(TriggerAction.LOG_TO_FILE)

    # Create trigger based on type
    if trigger_type == TriggerType.VARIABLE_THRESHOLD:
        var_name = dpg.get_value("var_name_input")
        comparison_str = dpg.get_value("comparison_input")
        threshold = dpg.get_value("threshold_input")

        # Map comparison string to enum
        comparison_map = {
            ">": TriggerComparison.GREATER_THAN,
            "<": TriggerComparison.LESS_THAN,
            ">=": TriggerComparison.GREATER_EQUAL,
            "<=": TriggerComparison.LESS_EQUAL,
            "==": TriggerComparison.EQUAL,
            "!=": TriggerComparison.NOT_EQUAL
        }

        trigger = TriggerCondition(
            trigger_id=trigger_id,
            name=name,
            enabled=True,
            trigger_type=trigger_type,
            variable_name=var_name,
            comparison=comparison_map.get(comparison_str, TriggerComparison.GREATER_THAN),
            threshold_value=threshold,
            actions=actions
        )

    elif trigger_type == TriggerType.MESSAGE_PATTERN:
        pattern = dpg.get_value("pattern_input")
        is_regex = dpg.get_value("regex_checkbox")

        trigger = TriggerCondition(
            trigger_id=trigger_id,
            name=name,
            enabled=True,
            trigger_type=trigger_type,
            message_pattern=pattern,
            pattern_is_regex=is_regex,
            actions=actions
        )

    elif trigger_type == TriggerType.MESSAGE_RATE:
        rate_threshold = dpg.get_value("rate_threshold_input")
        rate_window = dpg.get_value("rate_window_input")

        trigger = TriggerCondition(
            trigger_id=trigger_id,
            name=name,
            enabled=True,
            trigger_type=trigger_type,
            rate_threshold=rate_threshold,
            rate_window=rate_window,
            actions=actions
        )
    else:
        return

    # Add trigger to engine
    app._trigger_engine.add_trigger(trigger)

    # Refresh trigger list
    _refresh_trigger_list(app)

    # Close dialog
    dpg.delete_item(dialog_tag)


def _refresh_trigger_list(app: UartiumApp) -> None:
    """Refresh the trigger list display."""
    # Clear existing list
    children = dpg.get_item_children("trigger_list_window", slot=1)
    if children:
        for child in children:
            dpg.delete_item(child)

    # Remove placeholder
    if dpg.does_item_exist("trigger_list_placeholder"):
        dpg.delete_item("trigger_list_placeholder")

    # Add triggers
    for trigger in app._trigger_engine.triggers.values():
        _add_trigger_to_list(app, trigger)


def _add_trigger_to_list(app: UartiumApp, trigger: TriggerCondition) -> None:
    """Add a single trigger to the list."""
    with dpg.group(parent="trigger_list_window", horizontal=False):
        with dpg.group(horizontal=True):
            # Enable/disable checkbox
            dpg.add_checkbox(
                default_value=trigger.enabled,
                callback=lambda s, v: app._trigger_engine.enable_trigger(trigger.trigger_id, v)
            )

            # Trigger name and description
            desc = _get_trigger_description(trigger)
            color = (80, 250, 123, 255) if trigger.enabled else (128, 128, 128, 255)
            dpg.add_text(f"{trigger.name}: {desc}", color=color)

            # Fire count
            dpg.add_text(f"(Fired: {trigger.fire_count})", color=(200, 200, 200, 255))

            # Delete button
            dpg.add_button(
                label="Delete",
                callback=lambda: _delete_trigger(app, trigger.trigger_id),
                width=60
            )

        dpg.add_separator()


def _get_trigger_description(trigger: TriggerCondition) -> str:
    """Get human-readable description of a trigger."""
    if trigger.trigger_type == TriggerType.VARIABLE_THRESHOLD:
        return f"{trigger.variable_name} {trigger.comparison.value} {trigger.threshold_value}"
    elif trigger.trigger_type == TriggerType.MESSAGE_PATTERN:
        pattern_type = "regex" if trigger.pattern_is_regex else "text"
        return f"Message contains ({pattern_type}): '{trigger.message_pattern}'"
    elif trigger.trigger_type == TriggerType.MESSAGE_RATE:
        return f"Rate > {trigger.rate_threshold} msg/s (window: {trigger.rate_window}s)"
    elif trigger.trigger_type == TriggerType.ERROR_COUNT:
        return f"Errors > {trigger.threshold_value} (window: {trigger.rate_window}s)"
    return "Unknown trigger type"


def _delete_trigger(app: UartiumApp, trigger_id: str) -> None:
    """Delete a trigger."""
    app._trigger_engine.remove_trigger(trigger_id)
    _refresh_trigger_list(app)


def _clear_all_triggers(app: UartiumApp) -> None:
    """Clear all triggers."""
    app._trigger_engine.clear_triggers()
    _refresh_trigger_list(app)

    # Restore placeholder
    if not dpg.does_item_exist("trigger_list_placeholder"):
        dpg.add_text(
            "(No triggers configured)",
            color=(128, 128, 128, 255),
            tag="trigger_list_placeholder",
            parent="trigger_list_window"
        )


def _save_trigger_config(app: UartiumApp) -> None:
    """Save trigger configuration to file."""
    try:
        app._trigger_engine.save_triggers("uartium_triggers.json")
        # Show success message in status bar
        if hasattr(app, '_status_text'):
            dpg.set_value(app._status_text, "[OK] Triggers saved to uartium_triggers.json")
            dpg.configure_item(app._status_text, color=(80, 250, 123, 255))
    except Exception as e:
        if hasattr(app, '_status_text'):
            dpg.set_value(app._status_text, f"[ERROR] Failed to save triggers: {e}")
            dpg.configure_item(app._status_text, color=(255, 82, 82, 255))


def _load_trigger_config(app: UartiumApp) -> None:
    """Load trigger configuration from file."""
    try:
        app._trigger_engine.load_triggers("uartium_triggers.json")
        _refresh_trigger_list(app)
        # Show success message
        if hasattr(app, '_status_text'):
            dpg.set_value(app._status_text, "[OK] Triggers loaded from uartium_triggers.json")
            dpg.configure_item(app._status_text, color=(80, 250, 123, 255))
    except Exception as e:
        if hasattr(app, '_status_text'):
            dpg.set_value(app._status_text, f"[ERROR] Failed to load triggers: {e}")
            dpg.configure_item(app._status_text, color=(255, 82, 82, 255))


def update_trigger_history(app: UartiumApp, trigger_event) -> None:
    """Update the trigger history display."""
    # Remove placeholder if exists
    if dpg.does_item_exist("trigger_history_placeholder"):
        dpg.delete_item("trigger_history_placeholder")

    # Add new history entry
    timestamp_str = time.strftime("%H:%M:%S", time.localtime(trigger_event.timestamp))
    history_text = f"{timestamp_str} - {trigger_event.trigger_name}: {trigger_event.message}"

    # Keep only last 20 entries
    children = dpg.get_item_children("trigger_history_window", slot=1)
    if children and len(children) > 20:
        dpg.delete_item(children[0])

    dpg.add_text(
        history_text,
        color=(255, 193, 7, 255),
        parent="trigger_history_window"
    )
