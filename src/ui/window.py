import os
import json
import threading
from gi.repository import Gtk, WebKit2, GLib
from core.package_manager import (
    get_installed_packages,
    get_flatpak_installed,
    get_updates,
    get_explore_packages,
    search_packages,
    install_package_app_store,
    uninstall_package_app_store
)

class AppStoreWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Linux Mobile App Store")
        self.set_default_size(400, 700)
        self.set_resizable(True) # Make the window resizable

        self.webview = WebKit2.WebView()
        self.add(self.webview)

        self.context = self.webview.get_user_content_manager()
        self.context.register_script_message_handler("appstore")
        self.context.connect("script-message-received::appstore", self.on_js_message)

        self.load_ui()
        
    def load_ui(self):
        """
        Loads the HTML UI into the WebView.
        Assumes 'index.html' is in the resources directory.
        """
        try:
            # src/ui/window.py -> src/ui/resources/index.html
            script_dir = os.path.dirname(os.path.abspath(__file__))
            html_file_path = os.path.join(script_dir, "resources", "index.html")

            if not os.path.exists(html_file_path):
                print(f"Error: index.html not found at {html_file_path}")
                # Fallback HTML for error display
                self.webview.load_html("<h1>Error: index.html not found!</h1><p>Please ensure 'index.html' is in the correct directory.</p>", "file:///")
                return

            with open(html_file_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            self.webview.load_html(html_content, f"file://{html_file_path}") # Use file:/// for correct base URL
            print(f"Loaded HTML from {html_file_path}")

        except Exception as e:
            print(f"Failed to load HTML: {e}")
            self.webview.load_html(f"<h1>Error loading UI: {e}</h1>", "file:///")


    def on_js_message(self, user_content_manager, js_message):
        """
        Handles messages sent from JavaScript to the Python backend.
        """
        message = js_message.get_js_value()
        json_str = ""
        try:
            json_str = message.to_string()
            message_dict = json.loads(json_str)

            command = message_dict.get('command')
            print(f"DEBUG: Received JS command: {command}, raw message: {json_str}")

            # Use GLib.idle_add for immediate responses back to JS on the main thread
            # Use threading.Thread for long-running operations (like package installs)

            if command == 'getInstalled':
                # Fetching can be long, so run in thread for better responsiveness
                threading.Thread(target=lambda: GLib.idle_add(
                    self.send_to_js, {'response': 'installedPackages', 'data': get_installed_packages() + get_flatpak_installed()}
                )).start()

            elif command == 'getUpdates':
                threading.Thread(target=lambda: GLib.idle_add(
                    self.send_to_js, {'response': 'updatePackages', 'data': get_updates()}
                )).start()

            elif command == 'getExplorePackages':
                threading.Thread(target=lambda: GLib.idle_add(
                    self.send_to_js, {'response': 'explorePackages', 'data': get_explore_packages()}
                )).start()
                
            elif command == 'search':
                term = message_dict.get('term')
                scope = message_dict.get('scope', 'installed')
                threading.Thread(target=self.run_search, args=(term, scope)).start()

            elif command == 'install' or command == 'uninstall':
                pkg = message_dict.get('package')
                is_install = (command == 'install')
                threading.Thread(target=self.run_install_uninstall, args=(pkg, is_install)).start()
            
            elif command == 'log':
                msg = message_dict.get('message')
                print(f"JS LOG: {msg}")
                
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON message from JS: {e} - Message: {json_str}")
        except Exception as e:
            print(f"Unhandled error handling JS message: {e}")

    def run_search(self, term, scope):
        """
        Runs the search operation in a background thread and sends results back to JS.
        """
        GLib.idle_add(self.send_to_js, {'response': 'operationStatus', 'status': f"Searching for '{term}'..."})
        results = search_packages(term, scope)
        GLib.idle_add(self.send_to_js, {'response': 'searchResults', 'data': results})
        GLib.idle_add(self.send_to_js, {'response': 'operationStatus', 'status': ""})

    def run_install_uninstall(self, pkg, is_install):
        """
        Executes install/uninstall commands in a background thread.
        Sends status updates and completion messages back to the JS frontend.
        """
        operation_name = 'install' if is_install else 'uninstall'
        pkg_id = pkg.get('raw_name') if pkg.get('source') == 'flatpak' and pkg.get('raw_name') else pkg.get('name')
        
        result = ""
        if is_install:
            result = install_package_app_store(pkg, self.send_to_js) # Use app store specific install
        else:
            result = uninstall_package_app_store(pkg, self.send_to_js) # Use app store specific uninstall

        success = "Error:" not in result 
        
        GLib.idle_add(self.send_to_js, {
            'response': 'operationCompleted',
            'id': pkg_id,
            'success': success,
            'message': result
        })
        
        # After operation, trigger a full UI refresh in JS
        GLib.idle_add(self.send_to_js, {'response': 'refresh'})

    def send_to_js(self, obj):
        """
        Sends a Python dictionary (converted to JSON string) to the JavaScript frontend.
        """
        try:
            js_code = f'window.appstoreReceive({json.dumps(obj)});'
            self.webview.run_javascript(js_code)
        except Exception as e:
            print(f"Error sending message to JS: {e}")
