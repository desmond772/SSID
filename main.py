import platform
import subprocess
import re
import logging
import os
import json
from dotenv import load_dotenv

# Load environment variables from a .env file
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
    """
    Extract the SSID on a Linux (including Termux) system.
    It first tries the termux-api and falls back to iwgetid if it fails.
    """
    try:
        # Try the recommended termux-api first.
        result = subprocess.run(
            ["termux-wifi-connectioninfo"],
            capture_output=True,
            text=True,
            check=False, # Don't raise an exception immediately
            timeout=10
        )

        # Log any non-zero exit code or error output
        if result.returncode != 0:
            logging.debug(f"termux-wifi-connectioninfo failed with exit code {result.returncode}. Stderr: {result.stderr.strip()}")
            raise ExtractionError("termux-wifi-connectioninfo failed, falling back.")

        # If stdout is empty, it's likely a permission issue
        if not result.stdout.strip():
            logging.debug("termux-wifi-connectioninfo returned empty output, likely a permissions issue. Falling back.")
            raise ExtractionError("termux-wifi-connectioninfo returned empty output.")
            
        info = json.loads(result.stdout)
        return info.get("ssid")

    except (ExtractionError, subprocess.TimeoutExpired) as e:
        # If termux-api fails, fall back to iwgetid for standard Linux
        logging.warning(f"Termux-api failed: {e}. Falling back to iwgetid.")
        try:
            output = subprocess.check_output(
                ["iwgetid", "-r"],
                universal_newlines=True,
                text=True
            ).strip()
            return output if output else None
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise ExtractionError(f"Error executing fallback 'iwgetid' command on Linux: {e}")
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from termux-wifi-connectioninfo. Raw output: '{result.stdout.strip()}'")
        raise ExtractionError(f"Error parsing termux-api output: {e}")

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

