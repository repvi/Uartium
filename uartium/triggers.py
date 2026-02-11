"""
Uartium - Trigger and Alert Engine
===================================

Provides automated monitoring and alerting for critical conditions:
  - Variable threshold triggers (>, <, ==, !=, >=, <=)
  - Regex pattern matching in messages
  - Message rate monitoring
  - Configurable actions: visual alerts, audio alerts, logging
  - Trigger history tracking
  - Save/load trigger configurations
"""

from __future__ import annotations
import re
import time
import json
import os
from typing import Callable, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TriggerType(Enum):
    """Types of triggers supported."""
    VARIABLE_THRESHOLD = "variable_threshold"
    MESSAGE_PATTERN = "message_pattern"
    MESSAGE_RATE = "message_rate"
    ERROR_COUNT = "error_count"


class TriggerComparison(Enum):
    """Comparison operators for threshold triggers."""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="


class TriggerAction(Enum):
    """Actions to take when trigger fires."""
    VISUAL_ALERT = "visual_alert"
    AUDIO_ALERT = "audio_alert"
    LOG_TO_FILE = "log_to_file"
    PAUSE_CAPTURE = "pause_capture"
    HIGHLIGHT_MESSAGE = "highlight_message"


@dataclass
class TriggerCondition:
    """Definition of a trigger condition."""
    trigger_id: str
    name: str
    enabled: bool
    trigger_type: TriggerType

    # For variable threshold triggers
    variable_name: Optional[str] = None
    comparison: Optional[TriggerComparison] = None
    threshold_value: Optional[float] = None

    # For message pattern triggers
    message_pattern: Optional[str] = None
    pattern_is_regex: bool = False

    # For rate triggers
    rate_threshold: Optional[float] = None  # messages per second
    rate_window: float = 60.0  # time window in seconds

    # Actions
    actions: list[TriggerAction] = None

    # Metadata
    created_at: float = 0.0
    fire_count: int = 0
    last_fired: Optional[float] = None

    def __post_init__(self):
        if self.actions is None:
            self.actions = [TriggerAction.VISUAL_ALERT]
        if self.created_at == 0.0:
            self.created_at = time.time()


@dataclass
class TriggerEvent:
    """Record of a trigger firing."""
    trigger_id: str
    trigger_name: str
    timestamp: float
    message: str
    details: dict


class TriggerEngine:
    """Engine for evaluating triggers and executing actions."""

    def __init__(self):
        self.triggers: dict[str, TriggerCondition] = {}
        self.history: list[TriggerEvent] = []
        self.max_history = 1000

        # Message rate tracking
        self._message_timestamps: list[float] = []
        self._error_count_window: list[tuple[float, int]] = []

        # Callbacks for actions
        self.on_visual_alert: Optional[Callable[[TriggerEvent], None]] = None
        self.on_audio_alert: Optional[Callable[[TriggerEvent], None]] = None
        self.on_log_trigger: Optional[Callable[[TriggerEvent], None]] = None
        self.on_pause_capture: Optional[Callable[[TriggerEvent], None]] = None

    def add_trigger(self, trigger: TriggerCondition) -> None:
        """Add a new trigger condition."""
        self.triggers[trigger.trigger_id] = trigger

    def remove_trigger(self, trigger_id: str) -> None:
        """Remove a trigger condition."""
        if trigger_id in self.triggers:
            del self.triggers[trigger_id]

    def enable_trigger(self, trigger_id: str, enabled: bool = True) -> None:
        """Enable or disable a trigger."""
        if trigger_id in self.triggers:
            self.triggers[trigger_id].enabled = enabled

    def clear_triggers(self) -> None:
        """Remove all triggers."""
        self.triggers.clear()

    def evaluate_message(self, msg: dict) -> list[TriggerEvent]:
        """
        Evaluate a message against all enabled triggers.

        Args:
            msg: Message dict with keys: timestamp, level, text, data_fields

        Returns:
            List of triggered events
        """
        fired_events = []

        # Track message for rate monitoring
        self._message_timestamps.append(msg.get("timestamp", time.time()))

        # Track errors for error count monitoring
        if msg.get("level") == "ERROR":
            self._error_count_window.append((msg.get("timestamp", time.time()), 1))

        # Clean old tracking data
        self._cleanup_tracking_data()

        # Evaluate each enabled trigger
        for trigger in self.triggers.values():
            if not trigger.enabled:
                continue

            event = self._evaluate_trigger(trigger, msg)
            if event:
                fired_events.append(event)
                self._record_trigger_fire(trigger, event)

        return fired_events

    def _evaluate_trigger(self, trigger: TriggerCondition, msg: dict) -> Optional[TriggerEvent]:
        """Evaluate a single trigger against a message."""

        if trigger.trigger_type == TriggerType.VARIABLE_THRESHOLD:
            return self._evaluate_variable_threshold(trigger, msg)

        elif trigger.trigger_type == TriggerType.MESSAGE_PATTERN:
            return self._evaluate_message_pattern(trigger, msg)

        elif trigger.trigger_type == TriggerType.MESSAGE_RATE:
            return self._evaluate_message_rate(trigger, msg)

        elif trigger.trigger_type == TriggerType.ERROR_COUNT:
            return self._evaluate_error_count(trigger, msg)

        return None

    def _evaluate_variable_threshold(self, trigger: TriggerCondition, msg: dict) -> Optional[TriggerEvent]:
        """Evaluate variable threshold trigger."""
        data_fields = msg.get("data_fields", {})

        if trigger.variable_name not in data_fields:
            return None

        var_info = data_fields[trigger.variable_name]
        value = var_info.get("value")

        # Convert to float for comparison
        try:
            value = float(value)
        except (ValueError, TypeError):
            return None

        # Evaluate comparison
        threshold = trigger.threshold_value
        comparison = trigger.comparison

        conditions = {
            TriggerComparison.GREATER_THAN: value > threshold,
            TriggerComparison.LESS_THAN: value < threshold,
            TriggerComparison.EQUAL: abs(value - threshold) < 1e-6,
            TriggerComparison.NOT_EQUAL: abs(value - threshold) >= 1e-6,
            TriggerComparison.GREATER_EQUAL: value >= threshold,
            TriggerComparison.LESS_EQUAL: value <= threshold,
        }

        if conditions.get(comparison, False):
            return TriggerEvent(
                trigger_id=trigger.trigger_id,
                trigger_name=trigger.name,
                timestamp=msg.get("timestamp", time.time()),
                message=f"{trigger.variable_name} {comparison.value} {threshold} (value={value})",
                details={
                    "variable": trigger.variable_name,
                    "value": value,
                    "threshold": threshold,
                    "comparison": comparison.value
                }
            )

        return None

    def _evaluate_message_pattern(self, trigger: TriggerCondition, msg: dict) -> Optional[TriggerEvent]:
        """Evaluate message pattern trigger."""
        text = msg.get("text", "")
        pattern = trigger.message_pattern

        if not pattern:
            return None

        # Match pattern
        if trigger.pattern_is_regex:
            try:
                if re.search(pattern, text):
                    return TriggerEvent(
                        trigger_id=trigger.trigger_id,
                        trigger_name=trigger.name,
                        timestamp=msg.get("timestamp", time.time()),
                        message=f"Pattern matched: {pattern}",
                        details={"pattern": pattern, "text": text}
                    )
            except re.error:
                pass  # Invalid regex
        else:
            if pattern in text:
                return TriggerEvent(
                    trigger_id=trigger.trigger_id,
                    trigger_name=trigger.name,
                    timestamp=msg.get("timestamp", time.time()),
                    message=f"Text contains: {pattern}",
                    details={"pattern": pattern, "text": text}
                )

        return None

    def _evaluate_message_rate(self, trigger: TriggerCondition, msg: dict) -> Optional[TriggerEvent]:
        """Evaluate message rate trigger."""
        current_time = msg.get("timestamp", time.time())
        window_start = current_time - trigger.rate_window

        # Count messages in window
        count = sum(1 for ts in self._message_timestamps if ts >= window_start)
        rate = count / trigger.rate_window

        if rate > trigger.rate_threshold:
            return TriggerEvent(
                trigger_id=trigger.trigger_id,
                trigger_name=trigger.name,
                timestamp=current_time,
                message=f"Message rate {rate:.2f} msg/s exceeds threshold {trigger.rate_threshold} msg/s",
                details={"rate": rate, "threshold": trigger.rate_threshold, "window": trigger.rate_window}
            )

        return None

    def _evaluate_error_count(self, trigger: TriggerCondition, msg: dict) -> Optional[TriggerEvent]:
        """Evaluate error count trigger."""
        current_time = msg.get("timestamp", time.time())
        window_start = current_time - trigger.rate_window

        # Count errors in window
        error_count = sum(cnt for ts, cnt in self._error_count_window if ts >= window_start)

        if error_count > trigger.threshold_value:
            return TriggerEvent(
                trigger_id=trigger.trigger_id,
                trigger_name=trigger.name,
                timestamp=current_time,
                message=f"Error count {error_count} exceeds threshold {trigger.threshold_value}",
                details={"error_count": error_count, "threshold": trigger.threshold_value, "window": trigger.rate_window}
            )

        return None

    def _record_trigger_fire(self, trigger: TriggerCondition, event: TriggerEvent) -> None:
        """Record that a trigger fired."""
        trigger.fire_count += 1
        trigger.last_fired = event.timestamp

        # Add to history
        self.history.append(event)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Execute actions
        self._execute_actions(trigger, event)

    def _execute_actions(self, trigger: TriggerCondition, event: TriggerEvent) -> None:
        """Execute configured actions for a trigger."""
        for action in trigger.actions:
            if action == TriggerAction.VISUAL_ALERT and self.on_visual_alert:
                self.on_visual_alert(event)
            elif action == TriggerAction.AUDIO_ALERT and self.on_audio_alert:
                self.on_audio_alert(event)
            elif action == TriggerAction.LOG_TO_FILE and self.on_log_trigger:
                self.on_log_trigger(event)
            elif action == TriggerAction.PAUSE_CAPTURE and self.on_pause_capture:
                self.on_pause_capture(event)

    def _cleanup_tracking_data(self) -> None:
        """Remove old tracking data outside of monitoring windows."""
        current_time = time.time()
        max_window = 300.0  # Keep 5 minutes of data
        cutoff = current_time - max_window

        # Clean message timestamps
        self._message_timestamps = [ts for ts in self._message_timestamps if ts >= cutoff]

        # Clean error count window
        self._error_count_window = [(ts, cnt) for ts, cnt in self._error_count_window if ts >= cutoff]

    def get_trigger_stats(self) -> dict:
        """Get statistics about triggers."""
        return {
            "total_triggers": len(self.triggers),
            "enabled_triggers": sum(1 for t in self.triggers.values() if t.enabled),
            "total_fires": sum(t.fire_count for t in self.triggers.values()),
            "history_count": len(self.history)
        }

    def save_triggers(self, filepath: str) -> None:
        """Save trigger configuration to file."""
        data = {
            "version": "1.0",
            "triggers": [
                {
                    **asdict(trigger),
                    "trigger_type": trigger.trigger_type.value,
                    "comparison": trigger.comparison.value if trigger.comparison else None,
                    "actions": [a.value for a in trigger.actions]
                }
                for trigger in self.triggers.values()
            ]
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_triggers(self, filepath: str) -> None:
        """Load trigger configuration from file."""
        if not os.path.exists(filepath):
            return

        with open(filepath, 'r') as f:
            data = json.load(f)

        self.triggers.clear()

        for trigger_data in data.get("triggers", []):
            # Convert enum values back
            trigger_data["trigger_type"] = TriggerType(trigger_data["trigger_type"])
            if trigger_data.get("comparison"):
                trigger_data["comparison"] = TriggerComparison(trigger_data["comparison"])
            trigger_data["actions"] = [TriggerAction(a) for a in trigger_data.get("actions", [])]

            trigger = TriggerCondition(**trigger_data)
            self.triggers[trigger.trigger_id] = trigger
