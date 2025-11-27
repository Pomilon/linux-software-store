import sys
import os
import gi
import signal

# Ensure GTK 3 and WebKit2 are available
try:
    gi.require_version('Gtk', '3.0')
    gi.require_version('WebKit2', '4.0')
    from gi.repository import Gtk
except ValueError:
    print("Error: GTK 3.0 or WebKit2 4.0 not found. Please ensure they are installed and configured correctly.")
    print("On Debian/Ubuntu: sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0")
    print("On Arch Linux: sudo pacman -S python-gobject gtk3 webkit2gtk")
    sys.exit(1)

from ui.window import AppStoreWindow
from core.package_manager import get_package_manager, check_package_installed, perform_initial_package_install
from utils.helpers import show_message_dialog

# Define a flag file path to mark that the initial check has been done
INITIAL_CHECK_FLAG_FILE = os.path.join(os.path.expanduser("~"), ".linux_app_store_initial_check_done")

def main_initial_check():
    """
    Performs the initial one-time package check and installation using GTK dialogs.
    Returns True if successful, False otherwise.
    """
    # Check if the flag file exists. If it does, skip the initial check.
    if os.path.exists(INITIAL_CHECK_FLAG_FILE):
        print("Initial package check already performed. Skipping.")
        return True

    # Define the list of packages for the initial check.
    required_initial_packages = [
        "python-gobject",
        "webkit2gtk",
        "gtk3"
    ]

    show_message_dialog("--- Starting Initial System Package Check ---", Gtk.MessageType.INFO)

    pkg_manager = get_package_manager()
    if not pkg_manager:
        show_message_dialog("Error: No supported package manager (apt, yum, dnf, pacman) found on this system.\nPlease ensure one of these is installed and in your PATH.", Gtk.MessageType.ERROR)
        return False 
    else:
        show_message_dialog(f"Detected system package manager: {pkg_manager}", Gtk.MessageType.INFO)

    missing_initial_packages = []
    for package in required_initial_packages:
        if not check_package_installed(package, pkg_manager):
            missing_initial_packages.append(package)

    if not missing_initial_packages:
        show_message_dialog("\nAll initial required packages are already installed. You're all set!", Gtk.MessageType.INFO)
        # Create the flag file as the initial check was successful
        try:
            with open(INITIAL_CHECK_FLAG_FILE, 'w') as f:
                f.write('done')
            print(f"Created flag file: {INITIAL_CHECK_FLAG_FILE}")
        except IOError as e:
            print(f"Warning: Could not create initial check flag file {INITIAL_CHECK_FLAG_FILE}: {e}")
        return True 
    else:
        missing_list = "\n".join([f"- {p}" for p in missing_initial_packages])
        show_message_dialog(f"--- Missing Initial Packages Detected ---\n{missing_list}\n\nAttempting to install missing packages...", Gtk.MessageType.WARNING)

        all_installed_initially = True
        for package in missing_initial_packages:
            if not perform_initial_package_install(package, pkg_manager):
                all_installed_initially = False
                break 

        if all_installed_initially:
            show_message_dialog("\n--- Initial Package Installation Finished Successfully ---", Gtk.MessageType.INFO)
            # Create the flag file as the initial check and installation was successful
            try:
                with open(INITIAL_CHECK_FLAG_FILE, 'w') as f:
                    f.write('done')
                print(f"Created flag file: {INITIAL_CHECK_FLAG_FILE}")
            except IOError as e:
                print(f"Warning: Could not create initial check flag file {INITIAL_CHECK_FLAG_FILE}: {e}")
            return True
        else:
            show_message_dialog("\n--- Initial Package Installation Aborted or Failed. Exiting. ---", Gtk.MessageType.ERROR)
            return False

def main():
    # Allow Ctrl+C to exit
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    Gtk.init() # Initialize GTK before any dialogs are created

    # Perform the one-time initial package check
    if main_initial_check():
        # Only launch the App Store GUI if initial checks/installs pass
        win = AppStoreWindow()
        win.connect("destroy", Gtk.main_quit)
        win.show_all()
        Gtk.main() # Start the main GTK loop for the App Store window
    else:
        Gtk.main_quit() # Quit if initial check failed or was aborted

if __name__ == "__main__":
    main()
