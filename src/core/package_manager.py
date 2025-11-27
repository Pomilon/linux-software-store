import subprocess
import re
from gi.repository import Gtk
from utils.helpers import show_message_dialog, show_confirmation_dialog, get_package_icon
from core.system import run_cmd, run_cmd_stream

# --- Core Package Management Functions (for initial check) ---
def get_package_manager():
    """
    Detects the system's package manager.
    Returns 'apt', 'yum', 'dnf', 'pacman', or None if none is found.
    """
    try:
        subprocess.run(['which', 'apt'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return 'apt'
    except subprocess.CalledProcessError:
        pass

    try:
        subprocess.run(['which', 'yum'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return 'yum'
    except subprocess.CalledProcessError:
        pass

    try:
        subprocess.run(['which', 'dnf'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return 'dnf'
    except subprocess.CalledProcessError:
        pass

    try:
        subprocess.run(['which', 'pacman'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return 'pacman'
    except subprocess.CalledProcessError:
        pass

    return None

def check_package_installed(package_name, pkg_manager):
    """
    Checks if a given package is installed based on the detected package manager.
    Returns True if installed, False otherwise.
    """
    print(f"Checking for package: {package_name}...") # Print to console for detailed log
    if pkg_manager == 'apt':
        try:
            result = subprocess.run(['dpkg', '-s', package_name], capture_output=True, text=True)
            return result.returncode == 0 and "install ok installed" in result.stdout.lower()
        except FileNotFoundError:
            show_message_dialog(f"Error: dpkg command not found. Is this an apt-based system?", Gtk.MessageType.ERROR)
            return False
    elif pkg_manager == 'yum' or pkg_manager == 'dnf':
        try:
            result = subprocess.run(['rpm', '-q', package_name], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            show_message_dialog(f"Error: rpm command not found. Is this an rpm-based system?", Gtk.MessageType.ERROR)
            return False
    elif pkg_manager == 'pacman':
        try:
            result = subprocess.run(['pacman', '-Q', package_name], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            show_message_dialog(f"Error: pacman command not found. Is this an Arch-based system?", Gtk.MessageType.ERROR)
            return False
    else:
        show_message_dialog(f"Warning: Cannot check package '{package_name}'. Unknown package manager.", Gtk.MessageType.WARNING)
        return False

def perform_initial_package_install(package_name, pkg_manager):
    """
    Prompts the user to install a package using GTK dialogs and executes the installation command if confirmed.
    This is for the initial, one-time check.
    """
    if pkg_manager is None:
        show_message_dialog(f"Cannot install '{package_name}': No supported package manager found.", Gtk.MessageType.ERROR)
        return False

    if show_confirmation_dialog(f"Package '{package_name}' is not installed.\nDo you want to install '{package_name}' using {pkg_manager}?"):
        install_command = []
        # Using pkexec for privileged operations
        if pkg_manager == 'apt':
            install_command = ['pkexec', pkg_manager, 'install', '-y', package_name]
        elif pkg_manager == 'yum' or pkg_manager == 'dnf':
            install_command = ['pkexec', pkg_manager, 'install', '-y', package_name]
        elif pkg_manager == 'pacman':
            install_command = ['pkexec', pkg_manager, '-S', '--noconfirm', package_name]
        else:
            show_message_dialog(f"Error: Installation for '{pkg_manager}' is not implemented.", Gtk.MessageType.ERROR)
            return False

        show_message_dialog(f"Attempting to install: {' '.join(install_command)}\n(You may be prompted for authentication.)", Gtk.MessageType.INFO)

        try:
            # Execute the installation command. User will be prompted for authentication.
            process = subprocess.run(install_command, check=True, text=True, capture_output=False)
            show_message_dialog(f"Package '{package_name}' installed successfully.", Gtk.MessageType.INFO)
            return True
        except subprocess.CalledProcessError as e:
            show_message_dialog(f"Error installing '{package_name}': {e}\nCheck terminal for details.", Gtk.MessageType.ERROR)
            print(f"STDOUT: {e.stdout}") # Still print to console for debugging
            print(f"STDERR: {e.stderr}")
            return False
        except FileNotFoundError:
            show_message_dialog("Error: pkexec or package manager command not found.", Gtk.MessageType.ERROR)
            return False
    else:
        show_message_dialog(f"Skipping installation of '{package_name}'.", Gtk.MessageType.INFO)
        return False

# --- Data Fetching Functions for App Store ---
def get_installed_packages():
    """
    Fetches a list of installed Pacman packages.
    Adds a source and mock icon to each package.
    """
    pacman_output = run_cmd(['pacman', '-Qi']) 
    pkgs = []
    if pacman_output.startswith("Error:"):
        print(f"Warning: {pacman_output}")
        return []
    
    blocks = pacman_output.split('\n\n')
    for block in blocks:
        pkg = {}
        for line in block.splitlines():
            if ': ' in line:
                key, value = line.split(': ', 1)
                key = key.strip()
                value = value.strip()
                if key == 'Name':
                    pkg['name'] = value
                elif key == 'Version':
                    pkg['version'] = value
                elif key == 'Description':
                    pkg['description'] = value
        if pkg.get('name'):
            pkg['source'] = 'pacman'
            pkg['icon'] = get_package_icon(pkg['name'])
            pkgs.append(pkg)
    return pkgs

def get_flatpak_installed():
    """
    Fetches a list of installed Flatpak applications.
    Adds a source and mock icon to each package.
    """
    flatpak_output = run_cmd(['flatpak', 'list', '--app', '--columns=application,version,description']) 
    pkgs = []
    if flatpak_output.startswith("Error:"):
        print(f"Warning: {flatpak_output}")
        return []
    
    for line in flatpak_output.splitlines():
        parts = line.split('\t')
        if len(parts) == 3:
            name = parts[0]
            version = parts[1]
            description = parts[2]
            display_name = name.split('.')[-1] if '.' in name else name
            
            pkgs.append({
                'name': display_name,
                'raw_name': name,
                'version': version,
                'description': description,
                'source': 'flatpak',
                'icon': get_package_icon(display_name)
            })
    return pkgs

def get_updates():
    """
    Checks for available Pacman and Flatpak updates.
    Adds a source and mock icon to each package.
    """
    updates = []

    pacman_out = run_cmd(['pacman', '-Qu']) 
    if pacman_out and not pacman_out.startswith("Error:"):
        for line in pacman_out.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                version = parts[1]
                updates.append({
                    'name': name,
                    'version': version,
                    'description': f'Update available to {version}',
                    'source': 'pacman',
                    'icon': get_package_icon(name)
                })
    
    flatpak_out = run_cmd(['flatpak', 'update', '--app', '--assumeno']) 
    if flatpak_out and not flatpak_out.startswith("Error:"):
        lines = flatpak_out.splitlines()
        for line in lines:
            if "Total:" in line or "Nothing to do" in line or "Skipping" in line:
                continue
            match = re.match(r'  ([a-zA-Z0-9\._-]+)\s+stable\s+([0-9\.]+)\s+([0-9\.]+)\s+.*', line)
            if match:
                raw_name = match.group(1)
                current_version = match.group(2)
                new_version = match.group(3)
                display_name = raw_name.split('.')[-1] if '.' in raw_name else raw_name
                updates.append({
                    'name': display_name,
                    'raw_name': raw_name,
                    'version': new_version,
                    'description': f"Update available from {current_version} to {new_version}",
                    'source': 'flatpak',
                    'icon': get_package_icon(display_name)
                })
    
    return updates

def search_pacman_repo(term):
    """
    Searches Pacman repositories for packages matching the term.
    """
    pacman_search_output = run_cmd(['pacman', '-Ss', term])
    found_pkgs = []
    if pacman_search_output.startswith("Error:"):
        print(f"Warning: {pacman_search_output}")
        return []

    package_blocks = re.split(r'\n\n', pacman_search_output)
    for block in package_blocks:
        lines = block.splitlines()
        if not lines:
            continue

        first_line_match = re.match(r'^(?:[a-z0-9-]+/)?([^ ]+) ([^ ]+)(?: \(([^)]+)\))?$', lines[0].strip())
        if first_line_match:
            name = first_line_match.group(1)
            version = first_line_match.group(2)
            description = ""
            if len(lines) > 1:
                desc_match = re.match(r'^\s+(.*)$', lines[1])
                if desc_match:
                    description = desc_match.group(1).strip()
            
            found_pkgs.append({
                'name': name,
                'version': version,
                'description': description,
                'source': 'pacman',
                'icon': get_package_icon(name)
            })
    return found_pkgs

def search_flatpak_repo(term):
    """
    Searches Flatpak remote repositories (specifically flathub) for applications.
    """
    flatpak_search_output = run_cmd(['flatpak', 'search', '--columns=application,version,description', term])
    found_pkgs = []
    if flatpak_search_output.startswith("Error:"):
        print(f"Warning: {flatpak_search_output}")
        return []
    
    for line in flatpak_search_output.splitlines():
        if line.lower().startswith('application\t'):
            continue
        parts = line.split('\t')
        if len(parts) >= 3:
            raw_name = parts[0].strip()
            version = parts[1].strip()
            description = parts[2].strip()
            display_name = raw_name.split('.')[-1] if '.' in raw_name else raw_name
            found_pkgs.append({
                'name': display_name,
                'raw_name': raw_name,
                'version': version,
                'description': description,
                'source': 'flatpak',
                'icon': get_package_icon(display_name)
            })
    return found_pkgs

def get_explore_packages():
    """
    Simulates fetching a list of available packages for the "Explore" tab.
    """
    # This function could be expanded to pull from actual repos like pacman -Slq and flatpak remote-ls --app
    # For now, it provides mock data.
    return [{
        'name': 'Vim',
        'version': '9.0',
        'description': 'A highly configurable text editor for efficient text editing.',
        'icon': get_package_icon('Vim'),
        'source': 'pacman',
        'status': 'available' 
    }, {
        'name': 'Firefox',
        'version': '127.0',
        'description': 'A fast, private and secure web browser.',
        'icon': get_package_icon('Firefox'),
        'source': 'flatpak',
        'status': 'available'
    }, {
        'name': 'GIMP',
        'version': '2.10.34',
        'description': 'GNU Image Manipulation Program, a free and open-source raster graphics editor.',
        'icon': get_package_icon('GIMP'),
        'source': 'pacman',
        'status': 'available'
    }, {
        'name': 'VLC Media Player',
        'version': '3.0.21',
        'description': 'Free and open source cross-platform multimedia player and framework.',
        'icon': get_package_icon('VLC Media Player'),
        'source': 'pacman',
        'status': 'available'
    }, {
        'name': 'Inkscape',
        'version': '1.2.2',
        'description': 'Professional vector graphics editor for Linux, Windows and macOS.',
        'icon': get_package_icon('Inkscape'),
        'source': 'flatpak',
        'status': 'available'
    }, {
        'name': 'Thunderbird',
        'version': '115.12.0',
        'description': 'Free email application that’s easy to set up and customize.',
        'icon': get_package_icon('Thunderbird'),
        'source': 'pacman',
        'status': 'available'
    }]

def search_packages(term, search_scope='installed'):
    """
    Searches packages based on the provided term and scope.
    """
    term = term.lower()
    
    all_packages = []
    if search_scope == 'installed':
        all_packages = get_installed_packages() + get_flatpak_installed()
    elif search_scope == 'explore':
        all_packages.extend(search_pacman_repo(term))
        all_packages.extend(search_flatpak_repo(term))
        # Remove duplicates based on name if they come from different sources
        unique_packages = {p['name']: p for p in all_packages}
        all_packages = list(unique_packages.values())
    else:
        return []

    results = [p for p in all_packages if term in p['name'].lower() or term in p['description'].lower()]
    return results

# --- Package Installation/Uninstallation for App Store (streaming progress) ---
def install_package_app_store(pkg_data, send_js_callback):
    """Installs a package using the specified source, reporting progress to JS."""
    pkg_name = pkg_data.get('name')
    source = pkg_data.get('source')
    raw_name = pkg_data.get('raw_name') # For Flatpak

    target_pkg_id = raw_name if source == 'flatpak' and raw_name else pkg_name

    print(f"DEBUG: Attempting to install {pkg_name} from {source}.")
    if source == 'pacman':
        # Using pkexec for privileged operations
        result = run_cmd_stream(['pkexec', 'pacman', '-S', '--noconfirm', pkg_name], target_pkg_id, 'install', pkg_name, send_js_callback)
    elif source == 'flatpak':
        # Flatpak might install to user or system. Assuming user for now if system is not desired, 
        # but store typically wants system-wide.
        # Flatpak typically handles its own polkit auth if needed, but let's check.
        # Flatpak install -y flathub ... might ask for password if installing system-wide.
        result = run_cmd_stream(['flatpak', 'install', '-y', 'flathub', target_pkg_id], target_pkg_id, 'install', pkg_name, send_js_callback)
    else:
        result = f"Error: Unknown source '{source}' for install."
    return result

def uninstall_package_app_store(pkg_data, send_js_callback):
    """Uninstalls a package using the specified source, reporting progress to JS."""
    pkg_name = pkg_data.get('name')
    source = pkg_data.get('source')
    raw_name = pkg_data.get('raw_name') # For Flatpak

    target_pkg_id = raw_name if source == 'flatpak' and raw_name else pkg_name

    print(f"DEBUG: Attempting to uninstall {pkg_name} from {source}.")
    if source == 'pacman':
        # Using pkexec for privileged operations
        result = run_cmd_stream(['pkexec', 'pacman', '-R', '--noconfirm', pkg_name], target_pkg_id, 'uninstall', pkg_name, send_js_callback)
    elif source == 'flatpak':
        result = run_cmd_stream(['flatpak', 'uninstall', '-y', target_pkg_id], target_pkg_id, 'uninstall', pkg_name, send_js_callback)
    else:
        result = f"Error: Unknown source '{source}' for uninstall."
    return result
