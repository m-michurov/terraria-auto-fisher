import time
from tkinter import messagebox
from typing import Any

from gui import AutoFisherGUI, PresetViewModel
from interaction import find_window, switch_window, click, screenshot, move_mouse, active_window_title, press
from motion_detector import MotionDetector
from preset import Preset
from statemachine import FishingStateMachine

SIZE = 92

GAME_WINDOW_TITLE = 'Terraria'
BUFF_HOTKEY = 'b'


class FishingBot:
    def __init__(self, terraria_window: Any) -> None:
        self._terraria_window = terraria_window
        self._running = False

        self._motion_detector = MotionDetector()
        self._state_machine = FishingStateMachine(cast=self._click, reel_in=self._click)
        self._preset = PresetViewModel(on_save=Preset.save, on_delete=Preset.delete)
        self._gui = AutoFisherGUI(
            presets=Preset.load_all(),
            view_model=self._preset,
            on_start=self._start,
            on_stop=self._stop
        )

    def _click(self) -> None:
        x, y = self._preset.screen_x.get(), self._preset.screen_y.get()
        move_mouse(position=(x, y + SIZE))
        click()

    def _start(self) -> None:
        time.sleep(0.1)
        switch_window(self._terraria_window)
        time.sleep(0.1)
        self._running = True

    def _stop(self) -> None:
        self._running = False
        self._state_machine.reset()

    def run(self) -> None:
        gui = self._gui
        motion_detector = self._motion_detector
        preset = self._preset
        state_machine = self._state_machine

        last_buff_time = time.time()

        while gui.open:
            with gui:
                motion_detector.frame_difference_threshold = preset.difference_threshold.get()
                motion_detector.sensitivity = preset.sensitivity.get()

                x, y = preset.screen_x.get(), preset.screen_y.get()
                region = (x - SIZE // 2, y - SIZE // 2, SIZE, SIZE)

                gui.region_preview = frame = screenshot(region=region)
                gui.game_active = game_active = f'{GAME_WINDOW_TITLE}:' in active_window_title()

                if not game_active:
                    continue

                gui.difference_preview, gui.motion_value, motion_detected = motion_detector.detect(frame)

                if not self._running:
                    continue

                state_machine.update(motion_detected)
                gui.status = state_machine.state_description

                buff_elapsed = time.time() - last_buff_time
                if not preset.use_buffs.get() or buff_elapsed < preset.buff_period.get():
                    continue

                press(BUFF_HOTKEY)
                last_buff_time = time.time()


def main() -> None:
    terraria_window = find_window(lambda title: title.startswith(f'{GAME_WINDOW_TITLE}:'))
    if terraria_window is None:
        messagebox.showerror(title=f'Error', message=f'Game window not found. Please launch {GAME_WINDOW_TITLE} first.')
        return

    bot = FishingBot(terraria_window)
    bot.run()


if __name__ == '__main__':
    main()
