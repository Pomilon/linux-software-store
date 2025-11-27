import subprocess
import re
from gi.repository import GLib

def run_cmd(cmd):
    """
    Executes a shell command and returns its standard output.
    Handles errors by returning an error string.
    """
    try:
        print(f"DEBUG: Attempting to run non-streaming command: {cmd}")
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        return f"Error: Command failed with exit code {e.returncode}. Stderr: {e.stderr.strip() if e.stderr else 'No stderr'}"
    except FileNotFoundError:
        return f"Error: Command '{cmd[0]}' not found. Make sure it's in your PATH."
    except subprocess.TimeoutExpired as e:
        return f"Error: Command '{cmd[0]}' timed out. Output: {e.stdout.strip() if e.stdout else ''} Error: {e.stderr.strip() if e.stderr else ''}"
    except Exception as e:
        return f"An unexpected error occurred while running command {cmd[0]}: {str(e)}"

def run_cmd_stream(cmd, pkg_id, command_type, pkg_name, send_js_callback):
    """
    Executes a shell command, streams its output, and sends progress updates
    to the JavaScript frontend via a callback.
    """
    try:
        print(f"DEBUG: Attempting to run streaming command: {cmd} for {pkg_name} ({command_type})")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1, # Line-buffered
            universal_newlines=True
        )

        progress = 0
        status = "Starting..."

        GLib.idle_add(send_js_callback, {
            'response': 'operationProgress',
            'id': pkg_id,
            'name': pkg_name,
            'command': command_type,
            'status': status,
            'progress': progress
        })

        # Read stdout line by line for progress
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            # print(f"STDOUT for {pkg_name}: {line}") # Keep this for debugging if needed

            # --- Progress Parsing Logic ---
            # Pacman download progress (e.g., ":: Downloading foo-bar 1.0.0-1 (50/100) ...")
            pacman_dl_match = re.search(r'\((\d+)/(\d+)\)', line)
            if pacman_dl_match:
                current_item = int(pacman_dl_match.group(1))
                total_items = int(pacman_dl_match.group(2))
                if total_items > 0:
                    progress = (current_item / total_items) * 100
                    status = f"Downloading item {current_item} of {total_items}"
                    GLib.idle_add(send_js_callback, {
                        'response': 'operationProgress',
                        'id': pkg_id,
                        'name': pkg_name,
                        'command': command_type,
                        'status': status,
                        'progress': progress
                    })
                    continue

            # Flatpak download/install progress (less standardized, often just "downloading", "installing")
            if "downloading" in line.lower():
                status = "Downloading..."
            elif "installing" in line.lower():
                status = "Installing..."
            elif "verifying" in line.lower():
                status = "Verifying..."
            elif "finishing" in line.lower():
                status = "Finishing..."
            
            # More generic percentage detection
            percent_match = re.search(r'(\d+)%', line)
            if percent_match:
                new_progress = int(percent_match.group(1))
                # Only update if progress increases or if it's the first percentage
                if new_progress >= progress: 
                    progress = new_progress
                    GLib.idle_add(send_js_callback, {
                        'response': 'operationProgress',
                        'id': pkg_id,
                        'name': pkg_name,
                        'command': command_type,
                        'status': status,
                        'progress': progress
                    })
                    continue 

            # Send general status updates if no specific progress was parsed
            if "error" in line.lower() or "failed" in line.lower():
                status = f"Error: {line}"
                GLib.idle_add(send_js_callback, {
                    'response': 'operationProgress',
                    'id': pkg_id,
                    'name': pkg_name,
                    'command': command_type,
                    'status': status,
                    'progress': progress
                })
            elif "warning" in line.lower():
                status = f"Warning: {line}"
            elif line: 
                status = line
                GLib.idle_add(send_js_callback, {
                    'response': 'operationProgress',
                    'id': pkg_id,
                    'name': pkg_name,
                    'command': command_type,
                    'status': status,
                    'progress': progress
                })
        
        # Ensure final state is reported
        if progress < 100 and "Error:" not in status:
            progress = 100 
            status = "Completed"
            GLib.idle_add(send_js_callback, {
                'response': 'operationProgress',
                'id': pkg_id,
                'name': pkg_name,
                'command': command_type,
                'status': status,
                'progress': progress
            })

        stdout_remaining, stderr = process.communicate()
        if stdout_remaining: 
            print(f"STDOUT (remaining) for {pkg_name}: {stdout_remaining.strip()}")

        if stderr:
            print(f"STDERR for {pkg_name}: {stderr.strip()}")

        if process.returncode != 0:
            return f"Error: Command failed with exit code {process.returncode}. Stderr: {stderr.strip() or 'No stderr'}"
        return "Success"

    except FileNotFoundError:
        return f"Error: Command '{cmd[0]}' not found. Make sure it's in your PATH."
    except subprocess.TimeoutExpired as e:
        process.kill()
        outs, errs = process.communicate()
        return f"Error: Command '{cmd[0]}' timed out. Output: {outs.strip() if outs else ''} Error: {errs.strip() if errs else ''}"
    except Exception as e:
        return f"An unexpected error occurred while running command {cmd[0]}: {str(e)}"
