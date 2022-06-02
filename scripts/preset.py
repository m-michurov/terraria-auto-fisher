import json
from dataclasses import dataclass
from pathlib import Path

from motion_detector import MotionDetector


__all__ = [
    'Preset'
]


@dataclass
class Preset:
    DEFAULT_NAME = 'Default'
    DEFAULT_BUFF_COOLDOWN = 60 * 3

    name: str = DEFAULT_NAME
    binarization_threshold: int = MotionDetector.BINARIZATION_THRESHOLD_DEFAULT
    sensitivity: int = MotionDetector.SENSITIVITY_DEFAULT
    difference_threshold: int = MotionDetector.DIFFERENCE_THRESHOLD_DEFAULT
    use_buffs: bool = False
    buff_period: int = DEFAULT_BUFF_COOLDOWN
    screen_x: int = 0
    screen_y: int = 0

    @staticmethod
    def load_all():
        return _load_presets()

    def delete(self):
        return _delete_preset(self)

    def save(self):
        return _save_preset(self)


_PRESETS_DIR = Path('presets')


def _preset_path(preset: Preset) -> Path:
    _PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    return _PRESETS_DIR / f'{preset.name}.json'


def _save_preset(preset: Preset) -> None:
    with open(_preset_path(preset), mode='w', encoding='utf-8') as preset_file:
        json.dump(preset.__dict__, preset_file, indent=4)


def _delete_preset(preset: Preset) -> None:
    _preset_path(preset).unlink(missing_ok=True)


def _load_preset(path: Path) -> Preset:
    preset = Preset()

    with open(path, mode='r', encoding='utf-8') as preset_file:
        for attr_name, attr_value in dict(json.load(preset_file)).items():
            setattr(preset, attr_name, attr_value)

    return preset


def _load_presets() -> list[Preset]:
    _PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    presets = list(map(_load_preset, _PRESETS_DIR.iterdir()))

    if any(preset.name == Preset.DEFAULT_NAME for preset in presets):
        return presets

    default = Preset()
    _save_preset(default)
    presets.append(default)

    return presets
