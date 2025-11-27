import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

# --- GTK Dialog Helper Functions (for initial prompts) ---
def show_message_dialog(message, dialog_type=Gtk.MessageType.INFO):
    """
    Displays a GTK message dialog.
    """
    # Parent is None here as this is used before the main AppStoreWindow is created
    dialog = Gtk.MessageDialog(
        parent=None,
        flags=0,
        message_type=dialog_type,
        buttons=Gtk.ButtonsType.OK,
        text=message
    )
    dialog.run()
    dialog.destroy()

def show_confirmation_dialog(message):
    """
    Displays a GTK confirmation dialog (Yes/No).
    Returns True if 'Yes' is clicked, False otherwise.
    """
    # Parent is None here as this is used before the main AppStoreWindow is created
    dialog = Gtk.MessageDialog(
        parent=None,
        flags=0,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.YES_NO,
        text=message
    )
    response = dialog.run()
    dialog.destroy()
    return (response == Gtk.ResponseType.YES)

# --- Mock Icon Data and Function ---
ICON_MAP = {
    'vim': 'fas fa-terminal',
    'firefox': 'fas fa-globe',
    'gimp': 'fas fa-paint-brush',
    'vlc': 'fas fa-play-circle',
    'inkscape': 'fas fa-vector-square',
    'thunderbird': 'fas fa-envelope',
    'htop': 'fas fa-chart-line',
    'neovim': 'fas fa-terminal',
    'krita': 'fas fa-paint-roller',
    'discord': 'fab fa-discord',
    'spotify': 'fab fa-spotify',
    'libreoffice': 'fas fa-file-alt',
}

def get_package_icon(pkg_name):
    """
    Returns a Font Awesome icon class or a default icon for a given package name.
    """
    return ICON_MAP.get(pkg_name.lower(), 'fas fa-cube')
