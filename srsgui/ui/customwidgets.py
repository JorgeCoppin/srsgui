from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit, QLineEdit, QSizePolicy, QMessageBox
from PySide6.QtCore import Qt, QTimer
from srsgui.utilities import log_action, log_queue, load_settings
from srsgui.ui.progresspopup import ProgressPopup
from srsgui.hardware.controller import SwitchboardController

class SwitchboardWidget(QWidget):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        settings = load_settings()
        self.startup_delay_1 = settings.get("startup_delay_1", 30)
        self.startup_delay_2 = settings.get("startup_delay_2", 150)
        self.shutdown_delay_1 = settings.get("shutdown_delay_1", 5)
        self.shutdown_delay_2 = settings.get("shutdown_delay_2", 5)

        self.start_phase = 0
        self.shutdown_phase = 0
        self.abort_event = False
        self.elapsed_time = 0
        self.is_starting = False
        self.is_shutting_down = False

        self.progress_popup = None

        self.init_ui()
        self.setup_timers()

    def init_ui(self):
        layout = QVBoxLayout()

        button_layout = QHBoxLayout()
        self.backing_btn, self.backing_light = self.create_instrument_control("Backing Pump", self.toggle_backing)
        self.turbo_btn, self.turbo_light = self.create_instrument_control("Turbo Pump", self.toggle_turbo)
        self.rga_btn, self.rga_light = self.create_instrument_control("RGA", self.toggle_rga)

        button_layout.addWidget(self.backing_btn)
        button_layout.addWidget(self.backing_light)
        button_layout.addWidget(self.turbo_btn)
        button_layout.addWidget(self.turbo_light)
        button_layout.addWidget(self.rga_btn)
        button_layout.addWidget(self.rga_light)

        for widget in [self.backing_btn, self.turbo_btn, self.rga_btn]:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        seq_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start System")
        self.shutdown_btn = QPushButton("Shutdown System")
        self.emergency_btn = QPushButton("EMERGENCY STOP")
        self.emergency_btn.setStyleSheet("background-color: red; color: white; font-weight: bold;")

        self.start_btn.clicked.connect(self.confirm_start)
        self.shutdown_btn.clicked.connect(self.confirm_shutdown)
        self.emergency_btn.clicked.connect(self.emergency_stop)

        seq_layout.addWidget(self.start_btn)
        seq_layout.addWidget(self.shutdown_btn)
        seq_layout.addWidget(self.emergency_btn)

        for widget in [self.start_btn, self.shutdown_btn, self.emergency_btn]:
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout.addLayout(button_layout)
        layout.addLayout(seq_layout)
        self.setLayout(layout)

    def create_instrument_control(self, label, toggle_func):
        btn = QPushButton(f"{label}: OFF")
        btn.clicked.connect(toggle_func)
        light = QLabel()
        light.setFixedSize(20, 20)
        light.setStyleSheet("background-color: red; border-radius: 10px;")
        return btn, light

    def toggle_backing(self):
        self.toggle_instrument("Backing", self.backing_btn, self.backing_light)

    def toggle_turbo(self):
        if not self.controller.status["Backing"]:
            log_action("ERROR: Cannot turn on Turbo Pump while Backing Pump is OFF!")
            return
        self.toggle_instrument("Turbo", self.turbo_btn, self.turbo_light)

    def toggle_rga(self):
        if not (self.controller.status["Backing"] and self.controller.status["Turbo"]):
            log_action("ERROR: Cannot turn on RGA unless Backing and Turbo are ON!")
            return
        self.toggle_instrument("RGA", self.rga_btn, self.rga_light)

    def toggle_instrument(self, name, button, light):
        current = self.controller.status[name]
        new_state = 0 if current else 1
        self.controller.set_status(name, new_state)
        button.setText(f"{name}: {'ON' if new_state else 'OFF'}")
        light.setStyleSheet(f"background-color: {'green' if new_state else 'red'}; border-radius: 10px;")

    def confirm_start(self):
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(self, "Start Sequence", "Are you sure you want to START?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.start_sequence()

    def confirm_shutdown(self):
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(self, "Shutdown Sequence", "Are you sure you want to SHUTDOWN?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.shutdown_sequence()

    def start_sequence(self):
        self.start_phase = 0
        self.is_starting = True
        self.is_shutting_down = False
        self.elapsed_time = 0
        self.show_progress_popup()
        self.start_next_phase()
        self.progress_timer.start(1000)

    def shutdown_sequence(self):
        self.shutdown_phase = 0
        self.is_shutting_down = True
        self.is_starting = False
        self.elapsed_time = 0
        self.show_progress_popup()
        self.shutdown_next_phase()
        self.progress_timer.start(1000)

    def start_next_phase(self):
        if self.abort_event:
            self.close_progress_popup()
            return
        if self.start_phase == 0:
            self.controller.set_status("Backing", 1)
            self.update_ui()
            self.start_phase += 1
            QTimer.singleShot(self.startup_delay_1 * 1000, self.start_next_phase)
        elif self.start_phase == 1:
            self.controller.set_status("Turbo", 1)
            self.update_ui()
            self.start_phase += 1
            QTimer.singleShot(self.startup_delay_2 * 1000, self.start_next_phase)
        elif self.start_phase == 2:
            self.controller.set_status("RGA", 1)
            self.update_ui()
            self.is_starting = False
            self.close_progress_popup()

    def shutdown_next_phase(self):
        if self.abort_event:
            self.close_progress_popup()
            return
        if self.shutdown_phase == 0:
            self.controller.set_status("RGA", 0)
            self.update_ui()
            self.shutdown_phase += 1
            QTimer.singleShot(self.shutdown_delay_1 * 1000, self.shutdown_next_phase)
        elif self.shutdown_phase == 1:
            self.controller.set_status("Turbo", 0)
            self.update_ui()
            self.shutdown_phase += 1
            QTimer.singleShot(self.shutdown_delay_2 * 1000, self.shutdown_next_phase)
        elif self.shutdown_phase == 2:
            self.controller.set_status("Backing", 0)
            self.update_ui()
            self.is_shutting_down = False
            self.close_progress_popup()

    def emergency_stop(self):
        self.abort_event = True
        self.controller.emergency_stop()
        self.update_ui()
        self.close_progress_popup()
        log_action("EMERGENCY STOP triggered!")

    def update_ui(self):
        for name, button, light in [("Backing", self.backing_btn, self.backing_light),
                                    ("Turbo", self.turbo_btn, self.turbo_light),
                                    ("RGA", self.rga_btn, self.rga_light)]:
            current = self.controller.status[name]
            button.setText(f"{name}: {'ON' if current else 'OFF'}")
            light.setStyleSheet(f"background-color: {'green' if current else 'red'}; border-radius: 10px;")

    def update_progress(self):
        if self.progress_popup:
            if self.is_starting:
                total = self.startup_delay_1 + self.startup_delay_2
                percent = min(int((self.elapsed_time / total) * 100), 100)
            elif self.is_shutting_down:
                total = self.shutdown_delay_1 + self.shutdown_delay_2
                percent = min(int((self.elapsed_time / total) * 100), 100)
            else:
                percent = 0
            self.progress_popup.progress_bar.setValue(percent)
        self.elapsed_time += 1

    def show_progress_popup(self):
        if not self.progress_popup:
            self.progress_popup = ProgressPopup(self.emergency_stop)
        self.progress_popup.progress_bar.setValue(0)
        self.progress_popup.show()

    def close_progress_popup(self):
        if self.progress_popup:
            self.progress_popup.close()
            self.progress_popup = None
        self.progress_timer.stop()

    def setup_timers(self):
        self.progress_timer = QTimer()
        self.progress_timer.timeout.connect(self.update_progress)

        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.check_heartbeat)
        self.heartbeat_timer.start(5000)

    def check_heartbeat(self):
        try:
            if not self.controller.i2c.try_lock():
                raise RuntimeError("I2C bus locked")
            self.controller.i2c.unlock()
        except Exception:
            log_action("CRITICAL: FT232H/MCP23008 lost! Emergency Stop triggered!")
            self.emergency_stop()

class LogWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        layout = QVBoxLayout()
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        layout.addWidget(self.log_display)

        self.note_label = QLabel("Enter Note:")
        self.note_entry = QLineEdit()
        self.note_entry.returnPressed.connect(self.save_note)
        layout.addWidget(self.note_label)
        layout.addWidget(self.note_entry)

        self.setLayout(layout)

    def setup_timer(self):
        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.poll_log_queue)
        self.log_timer.start(100)

    def poll_log_queue(self):
        while not log_queue.empty():
            msg = log_queue.get_nowait()
            self.log_display.append(msg)

    def save_note(self):
        note = self.note_entry.text().strip()
        if note:
            log_action("NOTE: " + note)
            self.note_entry.clear()
