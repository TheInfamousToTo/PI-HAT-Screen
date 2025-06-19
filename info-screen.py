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
    except (subprocess.CalledProcessError, ValueError) as e:
        logging.error(f"Failed to get CPU temperature: {e}")
        return "N/A" # Handle cases where temp might not be readable

def get_ram_usage():
    """Get RAM usage percentage."""
    ram = psutil.virtual_memory()
    return ram.percent # Percentage of RAM used

def get_cpu_usage():
    """Get CPU usage percentage."""
    # cpu_percent(interval=None) gets utilization since last call, suitable for loop
    return psutil.cpu_percent(interval=None)

def clear_and_exit(signum, frame):
    oled.fill(0)
    oled.show()
    sys.exit(0)

signal.signal(signal.SIGTERM, clear_and_exit)
signal.signal(signal.SIGINT, clear_and_exit)

def main():
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

if __name__ == "__main__":
    main()