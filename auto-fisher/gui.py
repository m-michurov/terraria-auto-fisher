import json
import tkinter as tk
from dataclasses import fields
from tkinter import ttk
from typing import Collection, Callable, Any

import numpy as np
import pyautogui as pg
from PIL import Image, ImageTk

from .motion_detector import MotionDetector
from .preset import Preset

__all__ = [
    'PresetViewModel',
    'AutoFisherGUI'
]

_tk = tk.Tk()
_tk.withdraw()
del _tk


class PresetViewModel:
    def __init__(
            self,
            on_save: Callable[[Preset], None],
            on_delete: Callable[[Preset], None]
    ) -> None:
        self._on_save = on_save
        self._on_delete = on_delete

        self._name = tk.StringVar()
        self._binarization_threshold = tk.IntVar()
        self._sensitivity = tk.IntVar()
        self._difference_threshold = tk.IntVar()
        self._use_buffs = tk.BooleanVar()
        self._buff_period = tk.IntVar()
        self._screen_x = tk.IntVar()
        self._screen_y = tk.IntVar()

    name = property(lambda self: self._name)
    binarization_threshold = property(lambda self: self._binarization_threshold)
    sensitivity = property(lambda self: self._sensitivity)
    difference_threshold = property(lambda self: self._difference_threshold)
    use_buffs = property(lambda self: self._use_buffs)
    buff_period = property(lambda self: self._buff_period)
    screen_x = property(lambda self: self._screen_x)
    screen_y = property(lambda self: self._screen_y)

    def _preset(self) -> Preset:
        filed_values = {}

        for field in fields(Preset):
            filed_values[field.name] = getattr(self, field.name).get()

        return Preset(**filed_values)

    preset = property(_preset)

    def save(self):
        self._on_save(self.preset)

    def delete(self):
        self._on_delete(self.preset)

    def bind(self, preset: Preset) -> None:
        for field, value in preset.__dict__.items():
            getattr(self, field).set(value)


class AutoFisherGUI:
    _TITLE = 'Auto Fisher'
    _ICON = 'icon.ico'
    _SET_POSITION_HOTKEY = 'Alt-f'

    _PREFERENCES_PRESET_NAME = 'preset_name'

    def __init__(
            self,
            presets: Collection[Preset],
            view_model: PresetViewModel,
            on_start: Callable[[], None],
            on_stop: Callable[[], None]
    ) -> None:
        assert len(presets) > 0

        self._presets = {it.name: it for it in presets}
        self._on_start = on_start
        self._on_stop = on_stop

        self._view_model = view_model
        preset_name = _load_preferences().get(AutoFisherGUI._PREFERENCES_PRESET_NAME)
        preset = self._presets.get(preset_name) or next(preset for preset in presets)
        self._view_model.bind(preset)
        self._selected = self._view_model.name

        self._game_active = False

        self._open = True

        self._root = tk.Toplevel()
        self._root.iconbitmap(AutoFisherGUI._ICON)
        self._root.title(AutoFisherGUI._TITLE)
        self._root.protocol('WM_DELETE_WINDOW', lambda *_: setattr(self, '_open', False))
        self._root.bind(f'<{AutoFisherGUI._SET_POSITION_HOTKEY}>', lambda *_: self._update_screen_xy())

        self._configure_layout()
        self._preset_selection_changed()

    def __enter__(self) -> None:
        pass

    def __exit__(self, *_) -> None:
        self.update()

    def _configure_layout(self) -> None:
        root = self._root

        # region previews
        preview_frame = tk.LabelFrame(root)
        preview_frame.grid(column=0, row=0, sticky=tk.NS)
        row = 0
        tk.Label(preview_frame, text='Detection region').grid(column=0, row=row, sticky=tk.EW)
        row += 1
        self._region_preview = tk.Label(preview_frame)
        self._region_preview.grid(column=0, row=row)
        row += 1
        tk.Label(preview_frame, text='Frame difference').grid(column=0, row=row, sticky=tk.EW)
        row += 1
        self._difference_preview = tk.Label(preview_frame)
        self._difference_preview.grid(column=0, row=row)
        row += 1
        self._difference = tk.Label(preview_frame)
        self._difference.grid(column=0, row=row, sticky=tk.EW)
        row += 1
        self._motion_detected = tk.Label(preview_frame)
        self._motion_detected.grid(column=0, row=row, sticky=tk.EW)
        del preview_frame
        # endregion

        settings_and_controls_frame = tk.LabelFrame(root)
        settings_and_controls_frame.grid(column=1, row=0, sticky=tk.NS)

        # region settings
        settings_frame = tk.LabelFrame(settings_and_controls_frame)
        settings_frame.pack(anchor=tk.N, fill=tk.BOTH, expand=True)
        row = 0
        tk.Label(settings_frame, text='Detection region position') \
            .grid(columnspan=2, row=row, sticky=tk.EW)
        row += 1
        tk.Label(settings_frame, text=f'Use [{AutoFisherGUI._SET_POSITION_HOTKEY}] to set to mouse position') \
            .grid(columnspan=2, row=row, sticky=tk.EW)
        row += 1
        width, height = pg.size()
        tk.Label(settings_frame, text='X').grid(column=0, row=row, sticky=tk.E)
        tk.Spinbox(
            settings_frame,
            textvariable=self._view_model.screen_x,
            from_=0,
            to=width,
            width=10,
            increment=5,
            state='readonly'
        ).grid(column=1, row=row, sticky=tk.EW)
        row += 1
        tk.Label(settings_frame, text='Y').grid(column=0, row=row, sticky=tk.E)
        tk.Spinbox(
            settings_frame,
            textvariable=self._view_model.screen_y,
            from_=0,
            to=height,
            width=10,
            increment=5,
            state='readonly'
        ).grid(column=1, row=row, sticky=tk.EW)
        row += 1
        tk.Label(settings_frame, text='Motion detection settings').grid(columnspan=2, row=row, sticky=tk.EW)
        row += 1
        tk.Label(settings_frame, text='Binarization threshold').grid(column=0, row=row, sticky=tk.E)
        tk.Spinbox(
            settings_frame,
            textvariable=self._view_model.binarization_threshold,
            from_=MotionDetector.BINARIZATION_THRESHOLD_MIN,
            to=MotionDetector.BINARIZATION_THRESHOLD_MAX,
            width=10,
            state='readonly'
        ).grid(column=1, row=row, sticky=tk.EW)
        row += 1
        tk.Label(settings_frame, text='Sensitivity').grid(column=0, row=row, sticky=tk.E)
        tk.Spinbox(
            settings_frame,
            textvariable=self._view_model.sensitivity,
            from_=MotionDetector.SENSITIVITY_MIN,
            to=MotionDetector.SENSITIVITY_MAX,
            width=10,
            state='readonly'
        ).grid(column=1, row=row, sticky=tk.EW)
        row += 1
        tk.Label(settings_frame, text='Difference threshold').grid(column=0, row=row, sticky=tk.E)
        tk.Spinbox(
            settings_frame,
            textvariable=self._view_model.difference_threshold,
            from_=MotionDetector.DIFFERENCE_THRESHOLD_MIN,
            to=MotionDetector.DIFFERENCE_THRESHOLD_MAX,
            width=10,
            state='readonly'
        ).grid(column=1, row=row, sticky=tk.EW)
        row += 1
        tk.Label(settings_frame, text='Use buffs').grid(column=0, row=row, sticky=tk.E)
        tk.Checkbutton(
            settings_frame,
            variable=self._view_model.use_buffs,
            onvalue=True,
            offvalue=False
        ).grid(column=1, row=row, sticky=tk.W)
        row += 1
        tk.Label(settings_frame, text='Buff period').grid(column=0, row=row, sticky=tk.E)
        tk.Spinbox(
            settings_frame,
            textvariable=self._view_model.buff_period,
            from_=0,
            to=1_000,
            width=10,
            increment=5,
            state='readonly'
        ).grid(column=1, row=row, sticky=tk.EW)
        del settings_frame
        # endregion

        # region controls
        controls_frame = tk.LabelFrame(settings_and_controls_frame)
        controls_frame.pack(anchor=tk.S, fill=tk.BOTH, expand=True)
        controls_frame.columnconfigure(index=0, weight=1)
        controls_frame.columnconfigure(index=1, weight=1)
        row = 0
        tk.Label(controls_frame, text='Preset name').grid(columnspan=2, row=row, sticky=tk.EW)
        row += 1
        self._presets_dropdown = ttk.Combobox(
            controls_frame,
            textvariable=self._selected,
            values=list(self._presets.keys())
        )
        self._presets_dropdown.grid(columnspan=2, row=row, sticky=tk.EW)
        self._presets_dropdown.bind(
            '<<ComboboxSelected>>',
            func=lambda *_: self._preset_selection_changed()
        )
        row += 1
        tk.Button(controls_frame, text='Save', command=self._save_preset).grid(column=0, row=row, sticky=tk.NSEW)
        self._delete_preset_button = tk.Button(controls_frame, text='Delete', command=self._delete_preset)
        self._delete_preset_button.grid(column=1, row=row, sticky=tk.NSEW)
        row += 1
        self._start_button = tk.Button(controls_frame, text='Start Fishing')

        def on_start() -> None:
            self._on_start()
            self._start_button.configure(text='Continue Fishing')
            stop_button.configure(state=tk.ACTIVE)

        self._start_button.configure(command=on_start)
        self._start_button.grid(columnspan=2, row=row, sticky=tk.EW)
        row += 1
        stop_button = tk.Button(controls_frame, text='Stop Fishing', state=tk.DISABLED)

        def on_stop() -> None:
            self._on_stop()
            stop_button.configure(state=tk.DISABLED)
            self._start_button.configure(text='Start Fishing')

        stop_button.configure(command=on_stop)
        stop_button.grid(columnspan=2, row=row, sticky=tk.EW)
        del controls_frame
        # endregion

    def _update_screen_xy(self) -> None:
        x, y = pg.position()
        self._view_model.screen_x.set(x)
        self._view_model.screen_y.set(y)

    def _on_update(self) -> None:
        can_delete_preset = \
            len(self._presets) > 1 \
            and self._view_model.name.get() != Preset.DEFAULT_NAME \
            and self._view_model.name.get() in self._presets
        self._delete_preset_button.configure(state=tk.ACTIVE if can_delete_preset else tk.DISABLED)

        can_start = not self._game_active
        self._start_button.configure(state=tk.ACTIVE if can_start else tk.DISABLED)

    # region preset selection
    def _preset_selection_changed(self) -> None:
        _save_preferences(preset_name=self._selected.get())
        self._view_model.bind(self._presets[self._selected.get()])

    def _save_preset(self) -> None:
        preset = self._view_model.preset

        self._presets[preset.name] = preset
        self._presets_dropdown.configure(values=list(self._presets.keys()))
        self._view_model.save()
        _save_preferences(preset_name=preset.name)

    def _delete_preset(self) -> None:
        assert len(self._presets) > 1

        preset = self._view_model.preset

        assert preset.name != Preset.DEFAULT_NAME

        del self._presets[preset.name]

        self._presets_dropdown.configure(values=list(self._presets.keys()))
        self._view_model.delete()
        self._selected.set(next(name for name in self._presets.keys()))
        self._preset_selection_changed()

    # endregion

    # region set-only properties
    def region_preview(self, image: np.ndarray) -> None:
        _set_image(self._region_preview, image)

    region_preview = property(fset=region_preview)

    def difference_preview(self, image: np.ndarray) -> None:
        _set_image(self._difference_preview, image)

    difference_preview = property(fset=difference_preview)

    def motion_value(self, value: int) -> None:
        self._difference.configure(text=f'Difference: {value}')
        motion_detected = 'Yes' if value > self._view_model.difference_threshold.get() else 'No'
        self._motion_detected.configure(text=f'Motion: {motion_detected}')

    motion_value = property(fset=motion_value)

    def game_active(self, value: bool) -> None:
        self._game_active = value

        if not value:
            self.status = ''

    game_active = property(fset=game_active)

    def status(self, value: str) -> None:
        if not value:
            self._root.title(AutoFisherGUI._TITLE)
            return

        self._root.title(f'{AutoFisherGUI._TITLE}: {value}')

    status = property(fset=status)

    # endregion

    # region window controls
    @property
    def open(self) -> bool:
        return self._open

    def update(self) -> None:
        assert self._open

        self._on_update()

        self._root.update_idletasks()
        self._root.update()

    def close(self) -> None:
        self._open = False
        self._root.quit()

    # endregion


def _set_image(label: tk.Label, image: np.ndarray) -> None:
    image = Image.fromarray(image)
    image = ImageTk.PhotoImage(image)

    label.configure(image=image)
    label.image = image


_PREFERENCES_FILE = 'preferences.json'


def _save_preferences(**kwargs) -> None:
    preferences = _load_preferences()

    with open(_PREFERENCES_FILE, mode='w', encoding='utf-8') as preferences_file:
        json.dump(preferences | kwargs, preferences_file, indent=4)


def _load_preferences() -> dict[str, Any]:
    try:
        with open(_PREFERENCES_FILE, mode='r', encoding='utf-8') as preferences_file:
            return json.load(preferences_file)
    except FileNotFoundError:
        return {}
