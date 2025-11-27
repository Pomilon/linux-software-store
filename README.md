# Linux Software Store

A modular, lightweight software store for Linux systems, built with Python, GTK, and WebKit2.

> Originally meant for phone-based linux distros.

## Features

-   **Modular Architecture**: Clean separation of UI, core logic, and utilities.
-   **Multi-Package Manager Support**: Designed to work with `pacman`, `apt`, `yum`, `dnf`, and `flatpak`.
-   **Modern UI**: HTML/CSS/JS frontend rendered via WebKit2 for a responsive and customizable interface.
-   **Streaming Operations**: Real-time progress updates for package installations and updates.
-   **Privileged Operations**: Uses `pkexec` for secure authentication when root privileges are required.

## Structure

-   `src/main.py`: Entry point of the application.
-   `src/ui/`: Contains the UI logic and resources (HTML/CSS).
-   `src/core/`: Core logic for package management and system interactions.
-   `src/utils/`: Helper functions.

## Installation & Usage

1.  **Dependencies**:
    Ensure you have the following installed:
    -   Python 3
    -   GTK 3
    -   WebKit2GTK
    -   Python GObject bindings (`python-gobject` or `python3-gi`)
    -   `pkexec` (for privileged operations)

    *Debian/Ubuntu:*
    ```bash
    sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0 policykit-1
    ```

    *Arch Linux:*
    ```bash
    sudo pacman -S python-gobject gtk3 webkit2gtk polkit
    ```

2.  **Run the application**:
    ```bash
    python src/main.py
    ```

## Development

-   **Frontend**: Modify `src/ui/resources/index.html` to change the look and feel.
-   **Backend**: Add support for new package managers in `src/core/package_manager.py`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
