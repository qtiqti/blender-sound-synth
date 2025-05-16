import re
import bpy
from mathutils import Vector

# ------------------------------
# Парсинг и форматирование кадров
# ------------------------------
def parse_repeat_frames(repeat_str: str) -> list[int]:
    """Преобразует строку с номерами кадров в список чисел."""
    try:
        return [int(num) for num in re.findall(r'\d+', repeat_str)]
    except Exception as e:
        print(f"[Sound Synth] Ошибка парсинга repeat_frames: {e}")
        return []


def should_trigger_sound(entry, current_frame: int) -> bool:
    """Определяет, нужно ли запускать звук на текущем кадре."""
    repeat_list = parse_repeat_frames(entry.repeat_frames)
    in_main = entry.frame_start <= current_frame <= entry.frame_end
    in_repeat = current_frame in repeat_list
    interval = entry.repeat_interval
    after_end_interval = interval > 0 and (current_frame - entry.frame_end) % interval == 0 and current_frame > entry.frame_end
    return in_main or in_repeat or after_end_interval


def frames_to_list(frames_str: str) -> list[int]:
    """Конвертирует строку кадров в список чисел."""
    return [int(x) for x in frames_str.split(",") if x.strip().isdigit()]


def list_to_frames(frames_list: list[int]) -> str:
    """Конвертирует список чисел в строку кадров."""
    return ",".join(map(str, frames_list))


# ------------------------------
# Поиск свободного звукового канала
# ------------------------------
def get_available_channel(scene: bpy.types.Scene, obj: bpy.types.Object) -> int:
    """
    Находит первый свободный канал (1–32) в Sequence Editor для данного объекта.
    Мы помечаем дорожки по имени: если seq.name.startswith(obj.name), считаем его «своим».
    """
    used = {seq.channel for seq in scene.sequence_editor.sequences_all
            if seq.type == 'SOUND' and seq.name.startswith(obj.name)}
    for ch in range(1, 33):
        if ch not in used:
            return ch
    return 1


# ------------------------------
# Вставка звука в Timeline с volume и pan
# ------------------------------
def add_sound_to_timeline(
    scene: bpy.types.Scene,
    obj: bpy.types.Object,
    entry,
    sound: bpy.types.Sound,
    start_frame: int,
    end_frame: int,
    volume: float = 1.0,
    pan: float = 0.0
) -> bpy.types.Sequence:
    """
    Вставляет или обновляет звуковую дорожку в VSE:
      - name: "<object>_<sound>_<start_frame>"
      - frame_start, frame_final_end, volume, pan
    """
    if not scene.sequence_editor:
        scene.sequence_editor_create()

    # проверим, есть ли уже такой стрим
    existing = next((
        seq for seq in scene.sequence_editor.sequences_all
        if seq.type == 'SOUND'
           and seq.sound == sound
           and seq.frame_start == start_frame
           and seq.frame_final_end == end_frame
    ), None)
    if existing:
        existing.volume = volume
        existing.pan = pan
        return existing

    seq = scene.sequence_editor.sequences.new_sound(
        name=f"{obj.name}_{sound.name}_{start_frame}",
        filepath=sound.filepath,
        channel=get_available_channel(scene, obj),
        frame_start=start_frame
    )
    seq.frame_final_end = end_frame
    seq.volume = volume
    seq.pan = pan
    print(f"[Sound Synth] Добавлен звук '{sound.name}' на кадры {start_frame}-{end_frame}, "
          f"volume={volume:.2f}, pan={pan:.2f}")
    return seq
