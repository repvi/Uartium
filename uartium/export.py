"""
Uartium - Enhanced Export Module
=================================

Provides multi-format export capabilities:
  - CSV (enhanced with metadata)
  - JSON (structured data)
  - Plain text (human-readable)
  - Export filtered data only
  - Export graph data with timestamps
"""

from __future__ import annotations
import csv
import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from uartium.gui import UartiumApp


class ExportFormat:
    """Export format definitions."""
    CSV = "csv"
    JSON = "json"
    TXT = "txt"


def export_messages(
    app: UartiumApp,
    format: str = ExportFormat.CSV,
    include_graphs: bool = False,
    apply_filters: bool = False
) -> str:
    """
    Export messages and data to file.

    Args:
        app: Main application instance
        format: Export format (csv, json, or txt)
        include_graphs: Include graph data in export
        apply_filters: Only export messages matching current timeline filters

    Returns:
        Path to the exported file
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"uartium_export_{timestamp}.{format}"

    if format == ExportFormat.CSV:
        _export_csv(app, filename, include_graphs, apply_filters)
    elif format == ExportFormat.JSON:
        _export_json(app, filename, include_graphs, apply_filters)
    elif format == ExportFormat.TXT:
        _export_txt(app, filename, apply_filters)
    else:
        raise ValueError(f"Unsupported export format: {format}")

    return filename


def _export_csv(app: UartiumApp, filename: str, include_graphs: bool, apply_filters: bool) -> None:
    """Export to CSV format."""
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)

        # Header with metadata
        writer.writerow(['# Uartium Export'])
        writer.writerow(['# Export Time:', datetime.now().isoformat()])
        writer.writerow(['# Total Messages:', sum(app._level_counts.values())])
        writer.writerow(['# Filters Applied:', str(apply_filters)])
        writer.writerow([])

        # Main data header
        writer.writerow(['TIMESTAMP', 'EVENT_LEVEL', 'MESSAGE_TEXT', 'VARIABLE_NAME', 'VARIABLE_VALUE', 'VARIABLE_TYPE'])

        # Export from timeline messages (most complete data)
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            # Skip if filter is off and we're applying filters
            if apply_filters and not app._level_filters.get(level, True):
                continue

            for msg in app._timeline_messages.get(level, []):
                # Use device timestamp if available, otherwise PC timestamp
                ts = msg.get('device_timestamp', int(msg.get('timestamp', 0)))
                message_text = msg.get('text', '')

                # If message has variables, export each variable as a separate row
                if 'data_fields' in msg and msg['data_fields']:
                    for var_name, var_info in msg['data_fields'].items():
                        writer.writerow([
                            ts,
                            level,
                            message_text,
                            var_name,
                            var_info.get('value', 'N/A'),
                            var_info.get('type', 'str')
                        ])
                else:
                    # No variables - export message only
                    writer.writerow([
                        ts,
                        level,
                        message_text,
                        '',
                        '',
                        ''
                    ])

        # Export graph data if requested
        if include_graphs and hasattr(app, '_graph_data'):
            writer.writerow([])
            writer.writerow(['# Graph Data'])
            writer.writerow(['VARIABLE_NAME', 'TIMESTAMP', 'VALUE', 'TYPE'])

            for var_name, data in app._graph_data.items():
                var_type = data.get('type', 'unknown')
                for x, y in zip(data['x'], data['y']):
                    writer.writerow([var_name, x, y, var_type])


def _export_json(app: UartiumApp, filename: str, include_graphs: bool, apply_filters: bool) -> None:
    """Export to JSON format."""
    export_data = {
        "metadata": {
            "export_time": datetime.now().isoformat(),
            "application": "Uartium Enterprise UART Monitor",
            "version": "1.0",
            "total_messages": sum(app._level_counts.values()),
            "filters_applied": apply_filters,
            "level_counts": app._level_counts.copy()
        },
        "messages": [],
        "graphs": {}
    }

    # Export messages
    for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
        # Skip if filter is off and we're applying filters
        if apply_filters and not app._level_filters.get(level, True):
            continue

        for msg in app._timeline_messages.get(level, []):
            message_entry = {
                "timestamp": msg.get('timestamp', 0),
                "device_timestamp": msg.get('device_timestamp'),
                "level": level,
                "text": msg.get('text', ''),
                "data_fields": {}
            }

            # Add variables if present
            if 'data_fields' in msg and msg['data_fields']:
                for var_name, var_info in msg['data_fields'].items():
                    message_entry['data_fields'][var_name] = {
                        "value": var_info.get('value'),
                        "type": var_info.get('type', 'str')
                    }

            export_data['messages'].append(message_entry)

    # Export graph data if requested
    if include_graphs and hasattr(app, '_graph_data'):
        for var_name, data in app._graph_data.items():
            export_data['graphs'][var_name] = {
                "type": data.get('type', 'unknown'),
                "data_points": [
                    {"time": float(x), "value": float(y)}
                    for x, y in zip(data['x'], data['y'])
                ]
            }

    with open(filename, 'w', encoding='utf-8') as jsonfile:
        json.dump(export_data, jsonfile, indent=2, default=str)


def _export_txt(app: UartiumApp, filename: str, apply_filters: bool) -> None:
    """Export to plain text format."""
    with open(filename, 'w', encoding='utf-8') as txtfile:
        # Header
        txtfile.write("=" * 80 + "\n")
        txtfile.write("UARTIUM ENTERPRISE UART MONITOR - MESSAGE LOG\n")
        txtfile.write("=" * 80 + "\n")
        txtfile.write(f"Export Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        txtfile.write(f"Total Messages: {sum(app._level_counts.values())}\n")
        txtfile.write(f"Filters Applied: {apply_filters}\n")
        txtfile.write("=" * 80 + "\n\n")

        # Messages
        for level in ['DEBUG', 'INFO', 'WARNING', 'ERROR']:
            # Skip if filter is off and we're applying filters
            if apply_filters and not app._level_filters.get(level, True):
                continue

            messages = app._timeline_messages.get(level, [])
            if not messages:
                continue

            txtfile.write(f"\n[{level}] Messages ({len(messages)})\n")
            txtfile.write("-" * 80 + "\n")

            for msg in messages:
                ts = msg.get('timestamp', 0)
                timestamp_str = datetime.fromtimestamp(ts).strftime('%H:%M:%S.%f')[:-3]
                text = msg.get('text', '')

                txtfile.write(f"{timestamp_str} | {text}\n")

                # Add variables if present
                if 'data_fields' in msg and msg['data_fields']:
                    for var_name, var_info in msg['data_fields'].items():
                        value = var_info.get('value', 'N/A')
                        var_type = var_info.get('type', 'str')
                        txtfile.write(f"           {var_name} = {value} ({var_type})\n")

        txtfile.write("\n" + "=" * 80 + "\n")
        txtfile.write("END OF EXPORT\n")
        txtfile.write("=" * 80 + "\n")


def generate_python_plot_script(app: UartiumApp, filename: str = "uartium_plot.py") -> str:
    """
    Generate a standalone Python script using matplotlib to plot the graph data.

    Args:
        app: Main application instance
        filename: Output filename for the script

    Returns:
        Path to the generated script
    """
    if not hasattr(app, '_graph_data') or not app._graph_data:
        raise ValueError("No graph data available to export")

    script_content = '''#!/usr/bin/env python3
"""
Auto-generated Uartium Graph Visualization Script
Run this script with: python {filename}
Requires: matplotlib
Install with: pip install matplotlib
"""

import matplotlib.pyplot as plt
from datetime import datetime

# Export metadata
export_time = "{export_time}"
variables = {variables}

# Create figure and subplots
fig, axes = plt.subplots({n_plots}, 1, figsize=(12, {height}))
if {n_plots} == 1:
    axes = [axes]

# Plot each variable
{plot_code}

# Common formatting
for ax in axes:
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('Time (s)')
    ax.legend(loc='best')

plt.suptitle(f'Uartium Variable Trends - Exported {{export_time}}', y=0.995)
plt.tight_layout()
plt.show()
'''.format(
        filename=filename,
        export_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        variables=list(app._graph_data.keys()),
        n_plots=len(app._graph_data),
        height=max(8, len(app._graph_data) * 3),
        plot_code=_generate_plot_code(app)
    )

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(script_content)

    return filename


def _generate_plot_code(app: UartiumApp) -> str:
    """Generate matplotlib plotting code for each variable."""
    plot_lines = []

    for idx, (var_name, data) in enumerate(app._graph_data.items()):
        x_data = list(data['x'])
        y_data = list(data['y'])
        var_type = data.get('type', 'unknown')

        plot_lines.append(f"# Plot {idx + 1}: {var_name}")
        plot_lines.append(f"x_{idx} = {x_data}")
        plot_lines.append(f"y_{idx} = {y_data}")
        plot_lines.append(f"axes[{idx}].plot(x_{idx}, y_{idx}, marker='o', markersize=3, linewidth=1.5)")
        plot_lines.append(f"axes[{idx}].set_ylabel('{var_name} ({var_type})')")
        plot_lines.append(f"axes[{idx}].set_title('{var_name}')")
        plot_lines.append("")

    return "\n".join(plot_lines)
