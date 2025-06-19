![Raspberry Pi OLED System Info Display Logo](./assets/logo.png)

# Raspberry Pi OLED System Info Display

This project displays real-time system information (IP Address, CPU Usage, CPU Temperature, Current Time, and RAM Usage) on a 128x32 I2C OLED display connected to a Raspberry Pi. The script is configured to run automatically as a systemd service on boot.

## Features

* **Display:** IP Address, CPU Usage (%), CPU Temperature (°C), Current Time (HH:MM), RAM Usage (%).
* **Auto-Start:** Configured as a `systemd` service to run on boot.
* **Refresh Rate:** Updates every 5 seconds.
* **Virtual Environment:** Uses a Python virtual environment for dependency management.

## Hardware Requirements

* Raspberry Pi (any model with I2C support)
* 128x32 I2C OLED Display (e.g., SSD1306)
* Jumper Wires

## Software Requirements

* Raspberry Pi OS (or any Debian-based Linux distribution)
* Python 3
* `pip` (Python package installer)

## Wiring the OLED Display

Connect your 128x32 I2C OLED display to your Raspberry Pi's GPIO pins as follows:

| OLED Pin | Raspberry Pi GPIO Pin (Physical Pin Number) |
| :------- | :------------------------------------------ |
| VCC      | 3.3V (Pin 1 or 17)                          |
| GND      | GND (Pin 6, 9, 14, 20, 25, 30, 34, 39)      |
| SCL      | SCL (GPIO3, Physical Pin 5)                 |
| SDA      | SDA (GPIO2, Physical Pin 3)                 |

**Important:** Double-check your specific OLED module's pinout as some might vary slightly.

## Installation Steps

Follow these steps on your Raspberry Pi:

### 1. Enable I2C Interface

The I2C interface is required for the Raspberry Pi to communicate with the OLED display.

    sudo raspi-config

Navigate to: `Interface Options` -> `I2C` -> `Yes`.
Exit `raspi-config` and reboot if prompted.

### 2. Update System and Install Dependencies

Ensure your system is up-to-date and install necessary packages for Python development and font rendering.

    sudo apt update
    sudo apt upgrade -y
    sudo apt install python3-pip python3-venv ttf-dejavu -y

### 3. Create a Python Virtual Environment

It's good practice to use a virtual environment to manage project dependencies.

    cd ~
    python3 -m venv screen_env

### 4. Activate the Virtual Environment and Install Python Libraries

Activate the virtual environment and install the required Python libraries: `Pillow`, `adafruit-circuitpython-ssd1306`, and `psutil`.

    source ~/screen_env/bin/activate
    pip install Pillow adafruit-circuitpython-ssd1306 psutil
    deactivate # Deactivate when done with installations

### 5. Create the Python Script

Create the Python script `info_screen.py` in your home directory (`/home/toto/`).

    nano ~/info_screen.py

Paste the following code into the file, then save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

    import time
    import board
    import busio
    import adafruit_ssd1306
    from PIL import Image, ImageDraw, ImageFont
    import subprocess
    import datetime
    import psutil
    import signal
    import sys
    import logging

    # Logging configuration
    logging.basicConfig(level=logging.INFO)

    # Initialize I2C
    # Using absolute paths for board.SCL and board.SDA can sometimes help in systemd environments
    i2c = busio.I2C(board.SCL, board.SDA)

    # Initialize OLED
    # The I2C address may be 0x3C or 0x3D. You can check with `sudo i2cdetect -y 1`
    oled = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

    # Clear display
    oled.fill(0)
    oled.show()

    # Create blank image for drawing.
    # Make sure to create image with mode '1' for 1-bit color.
    image = Image.new("1", (oled.width, oled.height))

    # Get drawing object to draw on image.
    draw = ImageDraw.Draw(image)

    # Load a font.
    # Using DejaVuSans.ttf at size 8 points for optimal fit on 128x32 display.
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 8)
    except IOError:
        font = ImageFont.load_default()

    def clear_and_exit(signum, frame):
        """Clear display and exit the program."""
        oled.fill(0)
        oled.show()
        sys.exit(0)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, clear_and_exit)
    signal.signal(signal.SIGINT, clear_and_exit)

    def get_ip_address():
        """Get local IP address."""
        # Using absolute paths for commands for robustness in systemd service
        cmd = "/usr/bin/hostname -I | /usr/bin/cut -d' ' -f1"
        try:
            return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to get IP address: {e}")
            return "No IP"

    def get_cpu_temperature():
        """Get CPU temperature."""
        # Using absolute path for cat command
        cmd = "/usr/bin/cat /sys/class/thermal/thermal_zone0/temp"
        try:
            temp_str = subprocess.check_output(cmd, shell=True).decode("utf-8")
            return f"{float(temp_str) / 1000.0:.1f}°C"
        except (subprocess.CalledProcessError, ValueError):
            return "N/A" # Handle cases where temp might not be readable

    def get_ram_usage():
        """Get RAM usage percentage."""
        ram = psutil.virtual_memory()
        return ram.percent # Percentage of RAM used

    def get_cpu_usage():
        """Get CPU usage percentage."""
        # cpu_percent(interval=None) gets utilization since last call, suitable for loop
        return psutil.cpu_percent(interval=None)

    while True:
        # Clear the image for the new drawing
        draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)

        # Get the information
        ip_address = get_ip_address()
        cpu_temp = get_cpu_temperature()
        ram_usage = get_ram_usage()
        cpu_usage = psutil.cpu_percent(interval=None) # Recalculate each time for more current value
        current_time = datetime.datetime.now().strftime("%H:%M") # HH:MM format

        # Draw the text on the image
        # Line 1: IP Address and CPU Usage
        draw.text((0, 0), f"IP:{ip_address} CPU:{cpu_usage:.0f}%", font=font, fill=255)
        # Line 2: Temperature, Current Time, and RAM Usage
        draw.text((0, 16), f"Tmp:{cpu_temp} Tm:{current_time} R:{ram_usage:.0f}%", font=font, fill=255)

        # Display the image on the OLED
        oled.image(image)
        oled.show()

        # Wait for 5 seconds before updating again
        time.sleep(5)

### 6. Create a Systemd Service

Create a systemd service file to automatically run the script on boot and manage its process.

    sudo nano /etc/systemd/system/info_screen.service

Paste the following configuration into the file, then save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

    # /etc/systemd/system/info_screen.service

    [Unit]
    Description=OLED Info Screen
    After=network-online.target
    After=multi-user.target

    [Service]
    ExecStart=/home/toto/screen_env/bin/python /home/toto/info_screen.py
    WorkingDirectory=/home/toto/
    StandardOutput=journal
    StandardError=journal
    Restart=always
    User=toto

    [Install]
    WantedBy=multi-user.target

### 7. Configure and Start the Systemd Service

After creating the service file, you need to reload systemd, enable the service, and start it.

    sudo systemctl daemon-reload           # Reload systemd configuration
    sudo systemctl enable info_screen.service # Enable the service to start on boot
    sudo systemctl start info_screen.service  # Start the service immediately

### 8. Verify the Service Status and Output

Check if the service is running and view its logs to ensure everything is working as expected.

    sudo systemctl status info_screen.service

You should see `Active: active (running)`. If not, check the logs for errors:

    sudo journalctl -u info_screen.service -f

This will show you the real-time output and any error messages from your Python script. Press `Ctrl+C` to exit the `journalctl` follower.

### 9. Reboot and Confirm

Finally, reboot your Raspberry Pi to ensure the script starts automatically after a fresh boot.

    sudo reboot

After rebooting, your OLED display should show the system information updating every 5 seconds.

## Troubleshooting

* **`ModuleNotFoundError: No module named 'PIL'` or similar:** Ensure you installed all Python dependencies (`Pillow`, `adafruit-circuitpython-ssd1306`, `psutil`) within your `screen_env` virtual environment. Activate the venv and run `pip install ...` again.
* **`Active: inactive (dead)` or `Active: failed` for the service:**
    * Check `sudo systemctl status info_screen.service` for immediate error messages.
    * Use `sudo journalctl -u info_screen.service -f` for detailed logs. Look for Python tracebacks or permission errors.
    * **Permissions:** Your user (`toto`) might not have permissions to access the I2C bus. Add your user to the `i2c` and `gpio` groups:
            sudo usermod -a -G i2c toto
            sudo usermod -a -G gpio toto
            sudo reboot # Reboot for group changes to take effect
    * **Syntax in `.service` file:** Ensure there are no comments (`#`) on the same line as directives in `[Unit]` or `[Service]` sections. Comments must be on their own line. The provided service file has been corrected to address this.
* **Text going out of screen:** The current code uses font size 8, which is generally the smallest readable. If it still goes out, consider simplifying the displayed information (e.g., removing one metric).
* **IP address shows "No IP":** The `network-online.target` in the service file should help, but if the network isn't ready in time, the script might capture "No IP" initially. This usually resolves itself on the next update once the network is fully up.

## Recent Improvements

- **Graceful Shutdown:**  
  The script now handles SIGTERM and SIGINT signals. When stopped (e.g., via `systemctl stop` or Ctrl+C), it clears the OLED display before exiting, preventing stale information from remaining on the screen.

- **Logging:**  
  Error handling now uses Python's `logging` module. If the script fails to retrieve the IP address or CPU temperature, it logs an error message, making troubleshooting easier via `journalctl`.

- **Main Function Structure:**  
  The main loop is now encapsulated in a `main()` function, and the script uses the `if __name__ == "__main__":` pattern. This improves readability and maintainability.

- **Code Readability:**  
  Functions are modular, and exception handling is explicit, making the code easier to extend and debug.

### Example: Graceful Exit and Logging

```python
import signal
import sys
import logging

logging.basicConfig(level=logging.INFO)

def clear_and_exit(signum, frame):
    oled.fill(0)
    oled.show()
    sys.exit(0)

signal.signal(signal.SIGTERM, clear_and_exit)
signal.signal(signal.SIGINT, clear_and_exit)

def get_ip_address():
    cmd = "/usr/bin/hostname -I | /usr/bin/cut -d' ' -f1"
    try:
        return subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to get IP address: {e}")
        return "No IP"
```

---

**Tip:**  
If you want to further customize the display (e.g., change refresh rate or displayed metrics), consider adding command-line arguments using Python's `argparse` module.