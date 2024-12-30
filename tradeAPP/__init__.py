# __init__.py


import logging
from .log import Log
import os

def open_logs_in_terminal(log_file):
    import subprocess
    import platform

    system = platform.system()

    if system == 'Windows':
        subprocess.Popen(['cmd.exe', '/k', f'type {log_file} && powershell Get-Content {log_file} -Wait'])
    elif system == 'Darwin':  # macOS
        subprocess.Popen(['open', '-a', 'Console', log_file])
    elif system == 'Linux':
        subprocess.Popen(['x-terminal-emulator', '-e', f'tail -f {log_file}'])
    else:
        Log.usr(f"Unsupported OS: {system}")

def start_logging_terminals():
    log_files = [
        'logs/usr.log',
        'logs/auto.log',
        'logs/data.log',
        'logs/request.log',
        'logs/order.log'
    ]

    for log_file in log_files:
        if os.path.exists(log_file):
            Log.usr(f"Opening log file: {log_file}")
            open_logs_in_terminal(log_file)
        else:
            Log.usr(f"Log file {log_file} does not exist.")

# Configure logging
Log.setup_loggers()
# Start logging terminals
Log.usr("Starting logging Console...")
start_logging_terminals()
