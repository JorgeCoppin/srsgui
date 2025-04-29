import os
os.environ['BLINKA_FT232H'] = '1'
import board
import busio
from adafruit_mcp230xx.mcp23008 import MCP23008
from digitalio import Direction
from srsgui.utilities import log_action


class SwitchboardController:
    def __init__(self, i2c_addr=0x20):
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA)
            self.mcp = MCP23008(self.i2c, address=i2c_addr)
        except Exception as e:
            log_action(f"Error initializing MCP23008: {e}")
            raise

        self.pins = [self.mcp.get_pin(i) for i in range(8)]
        for pin in self.pins:
            pin.direction = Direction.OUTPUT

        self.status = {"Backing": 0, "Turbo": 0, "RGA": 0}
        self.last_status = self.status.copy()
        self.pin_mapping = {"Backing": 0, "Turbo": 3, "RGA": 6}
        self.update_all(force=True)

    def update_all(self, force=False):
        if force or self.status != self.last_status:
            for instrument, pin_index in self.pin_mapping.items():
                self.pins[pin_index].value = bool(self.status.get(instrument, 0))
            log_action(f"Updated switchboard: {self.status}")
            self.last_status = self.status.copy()

    def set_status(self, instrument, value):
        if instrument in self.status:
            self.status[instrument] = value
            self.update_all()

    def emergency_stop(self):
        for key in self.status:
            self.status[key] = 0
        self.update_all()
