import bpy
from . import utils


def get_available_channel(scene, obj):
    """Находит первый свободный канал для объекта."""
    used_channels = set()
    for seq in scene.sequence_editor.sequences_all:
        if seq.type == 'SOUND' and seq.name.startswith(obj.name):
            used_channels.add(seq.channel)

    # Ищем свободный канал (1-32)
    for channel in range(1, 33):
        if channel not in used_channels:
            return channel
    return 1  # Если все заняты, перезаписываем первый


def add_sound_to_timeline(scene, obj, entry, sound, start_frame, end_frame):
    """Добавляет звук в указанный интервал кадров."""
    existing_seq = next(
        (seq for seq in scene.sequence_editor.sequences_all
         if seq.sound == sound
         and seq.frame_start == start_frame
         and seq.frame_final_end == end_frame),
        None
    )

    if not existing_seq:
        try:
            seq = scene.sequence_editor.sequences.new_sound(
                name=f"{obj.name}_{sound.name}_{start_frame}",
                filepath=sound.filepath,
                channel=1,
                frame_start=start_frame
            )
            seq.frame_final_end = end_frame
            seq.volume = 1.0  # Громкость будет обновляться отдельно
            print(f"[DEBUG] Добавлен звук: {sound.name}, кадры {start_frame}-{end_frame}")
        except Exception as e:
            print(f"[Sound Synth] Ошибка: {e}")


def sound_playback(scene):
    cam = scene.camera
    if not cam:
        return

    current_frame = scene.frame_current

    for obj in scene.objects:
        if not obj.sound_synth_attached_sounds:
            continue

        entry = obj.sound_synth_attached_sounds[0]
        added_frames = utils.frames_to_list(entry.added_frames)
        sound = bpy.data.sounds.get(entry.sound_name)
        if not sound:
            continue

        # Расчёт громкости на основе расстояния
        distance = (obj.location - cam.location).length
        volume = max(0.1, 1 - distance / scene.sound_synth_attenuation_factor)

        # Основной интервал
        if current_frame == entry.frame_start and current_frame not in added_frames:
            add_sound_to_timeline(scene, obj, entry, sound, entry.frame_start, entry.frame_end)
            added_frames.append(current_frame)
            entry.added_frames = utils.list_to_frames(added_frames)

        # Повторы
        repeat_list = utils.parse_repeat_frames(entry.repeat_frames)
        if current_frame in repeat_list and current_frame not in added_frames:
            duration = entry.frame_end - entry.frame_start
            add_sound_to_timeline(scene, obj, entry, sound, current_frame, current_frame + duration)
            added_frames.append(current_frame)
            entry.added_frames = utils.list_to_frames(added_frames)

        # Обновить громкость всех дорожек этого звука
        for seq in scene.sequence_editor.sequences_all:
            if seq.sound == sound:
                seq.volume = volume
    # Принудительное обновление аудио
    bpy.ops.sequencer.refresh_all()

# def update_sound_volume(scene, obj, sound, volume):
#     """Обновляет громкость всех дорожек звука в VSE."""
#     if not scene.sequence_editor:
#         return
#
#     for seq in scene.sequence_editor.sequences_all:
#         if seq.type == 'SOUND' and seq.sound == sound:
#             seq.volume = volume
#             print(f"[Sound Synth] Обновлена громкость: {sound.name} → {volume:.2f}")
#
# def sound_playback(scene):
#     cam = scene.camera
#     if not cam:
#         print("[Sound Synth] Нет камеры на сцене.")
#         return
#
#     # Создать Sequence Editor, если отсутствует
#     if not scene.sequence_editor:
#         scene.sequence_editor_create()
#
#     current_frame = scene.frame_current
#
#     for obj in scene.objects:
#         if not hasattr(obj, "sound_synth_attached_sounds") or not obj.sound_synth_attached_sounds:
#             continue
#
#         entry = obj.sound_synth_attached_sounds[0]
#         sound = bpy.data.sounds.get(entry.sound_name)
#         if not sound:
#             continue
#
#         # Если автоматическое затухание выключено, пропустить
#         if not scene.sound_synth_attenuation_enable:
#             continue
#
#         # Расчёт расстояния до камеры
#         distance = (obj.location - cam.location).length
#
#         # Формула затухания (экспоненциальная)
#         attenuation_factor = scene.sound_synth_attenuation_factor
#         volume = 1.0 / (1.0 + (distance / attenuation_factor))
#         volume = max(0.1, min(1.0, volume))  # Минимум 10% громкости
#
#         # Обновить громкость всех дорожек
#         update_sound_volume(scene, obj, sound, volume)
#
#         # Добавить звук в таймлайн, если его ещё нет
#         existing_seq = next(
#             (seq for seq in scene.sequence_editor.sequences_all
#              if seq.type == 'SOUND' and seq.sound == sound),
#             None
#         )
#
#         if not existing_seq:
#             try:
#                 seq = scene.sequence_editor.sequences.new_sound(
#                     name=sound.name,
#                     filepath=sound.filepath,
#                     channel=1,
#                     frame_start=entry.frame_start
#                 )
#                 seq.frame_final_end = entry.frame_end
#                 seq.volume = volume
#                 print(f"[Sound Synth] Добавлен звук: {sound.name}")
#             except Exception as e:
#                 print(f"[Sound Synth] Ошибка: {e}")




