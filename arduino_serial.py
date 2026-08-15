try:
    import serial
    from serial.tools import list_ports as _list_ports
except Exception:
    serial = None
    _list_ports = None


class ArduinoSerial:
    """Simple Arduino serial helper.

    - If `pyserial` is not installed, methods will fail gracefully and `enabled` is False.
    - `send_status` writes newline-terminated ASCII commands: FAIL, PASS, OK, RESET
    """

    def __init__(self, port: str = "COM3", baudrate: int = 9600, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        self.enabled = False
        self._open_serial()

    def _open_serial(self):
        if serial is None:
            self.serial = None
            self.enabled = False
            return
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            self.enabled = True
        except Exception:
            self.serial = None
            self.enabled = False

    def send_status(self, message: str) -> bool:
        """Send a short status command to the Arduino. Returns True on success."""
        if not self.enabled or self.serial is None:
            return False
        payload = message.strip().upper()
        if payload not in {"FAIL", "PASS", "OK", "RESET"}:
            return False
        try:
            self.serial.write((payload + "\n").encode("utf-8"))
            self.serial.flush()
            return True
        except Exception:
            self.enabled = False
            return False

    def close(self):
        if self.serial is not None:
            try:
                self.serial.close()
            except Exception:
                pass
            finally:
                self.serial = None
                self.enabled = False


def list_serial_ports() -> list:
    """Return a list of available serial port device names, or empty list if unavailable."""
    if _list_ports is None:
        return []
    try:
        return [p.device for p in _list_ports.comports()]
    except Exception:
        return []
