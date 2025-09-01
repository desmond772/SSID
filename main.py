import platform
import subprocess
import re
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration (can be overridden by .env) ---
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

def setup_logging():
    """Configures the logging for the application."""
    logging.basicConfig(
        level=LOG_LEVEL,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

class ExtractionError(Exception):
    """Exception raised for errors during SSID extraction."""
    pass

class NotSupportedError(Exception):
    """Exception raised for unsupported operating systems."""
    pass

def _get_ssid_windows():
    """Extract the SSID on a Windows operating system."""
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "interfaces"],
            universal_newlines=True,
            text=True
        )
        match = re.search(r"SSID\s+:\s(.*)", output)
        if match:
            return match.group(1).strip()
        return None
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise ExtractionError(f"Error executing 'netsh' command on Windows: {e}")

def _get_ssid_linux():
    """Extract the SSID on a Linux operating system."""
    try:
        # Use iwgetid for a simple, quick way to get the SSID
        output = subprocess.check_output(
            ["iwgetid", "-r"],
            universal_newlines=True,
            text=True
        ).strip()
        return output if output else None
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise ExtractionError(f"Error executing 'iwgetid' command on Linux: {e}")

def _get_ssid_darwin():
    """Extract the SSID on a macOS operating system."""
    try:
        output = subprocess.check_output(
            ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
            universal_newlines=True,
            text=True
        )
        match = re.search(r"SSID:\s(.*)", output)
        if match:
            return match.group(1).strip()
        return None
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise ExtractionError(f"Error executing 'airport' command on macOS: {e}")

def get_current_ssid():
    """
    Returns the SSID of the connected Wi-Fi network.
    
    Raises:
        ExtractionError: If the SSID cannot be extracted.
        NotSupportedError: If the operating system is not supported.
    """
    os_name = platform.system()
    if os_name == "Windows":
        return _get_ssid_windows()
    elif os_name == "Linux":
        return _get_ssid_linux()
    elif os_name == "Darwin":  # macOS
        return _get_ssid_darwin()
    else:
        raise NotSupportedError(f"Operating system '{os_name}' is not supported.")

def main():
    """
    Main function to run the SSID extraction.
    """
    setup_logging()
    
    logging.info("Starting SSID extraction...")
    try:
        ssid = get_current_ssid()
        if ssid:
            logging.info(f"Connected SSID: {ssid}")
            return ssid
        else:
            logging.warning("No SSID found or not connected to a Wi-Fi network.")
            return None
    except NotSupportedError as e:
        logging.critical(e)
        return None
    except ExtractionError as e:
        logging.error(f"Failed to extract SSID: {e}")
        return None

if __name__ == "__main__":
    main()
  
