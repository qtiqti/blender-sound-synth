import bpy
import os
import tempfile
import webbrowser
import requests
from . import database
from . import dsp
from .utils import add_sound_to_timeline, get_available_channel, should_trigger_sound, frames_to_list, list_to_frames



def add_sound_with_repeats(scene, obj, sound, entry):
    if not scene.sequence_editor:
        scene.sequence_editor_create()

    # Добавляем основной интервал через нашу функцию
    add_sound_to_timeline(scene, obj, entry, sound, entry.frame_start, entry.frame_end)

    # Добавим повторы (если есть)
    if entry.repeat_interval > 0:
        duration = entry.frame_end - entry.frame_start
        repeat_frame = entry.frame_end + entry.repeat_interval
        while repeat_frame < scene.frame_end:
            add_sound_to_timeline(scene, obj, entry, sound, repeat_frame, repeat_frame + duration)
            repeat_frame += entry.repeat_interval



class SOUND_SYNTH_OT_LoadSound(bpy.types.Operator):
    bl_idname = "sound_synth.load_sound"
    bl_label = "Загрузить звук"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        try:
            sound = bpy.data.sounds.load(self.filepath, check_existing=True)

            for s in context.scene.sound_synth_sounds:
                if s.name == sound.name:
                    self.report({'WARNING'}, f"Звук '{sound.name}' уже загружен!")
                    return {'CANCELLED'}

            new_sound = context.scene.sound_synth_sounds.add()
            new_sound.name = sound.name

            context.scene.sound_synth_selected = sound.name
            if context.area:
                context.area.tag_redraw()

            self.report({'INFO'}, f"Звук '{sound.name}' загружен!")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Ошибка загрузки: {e}")
            return {'CANCELLED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SOUND_SYNTH_OT_AttachSound(bpy.types.Operator):
    bl_idname = "sound_synth.attach_sound"
    bl_label = "Привязать звук к объекту"

    def execute(self, context):
        obj = context.object
        scene = context.scene
        if not obj:
            self.report({'WARNING'}, "Нет активного объекта!")
            return {'CANCELLED'}
        selected_sound = scene.sound_synth_selected
        if not selected_sound:
            self.report({'WARNING'}, "Сначала выберите или добавьте звук!")
            return {'CANCELLED'}

        sound = bpy.data.sounds.get(selected_sound)
        if not sound:
            self.report({'ERROR'}, f"Звук '{selected_sound}' не найден!")
            return {'CANCELLED'}

        # Привязываем звук к объекту
        obj.sound_synth_attached_sounds.clear()
        entry = obj.sound_synth_attached_sounds.add()
        entry.sound_name = sound.name
        entry.frame_start = scene.freesound_start_frame
        entry.frame_end = scene.freesound_end_frame
        entry.repeat_frames = scene.freesound_repeat_frames
        entry.spectral_mod = scene.freesound_spectral_mod
        entry.added_frames = ""  # Сброс при привязке нового звука

        # Добавляем звук на таймлайн через функцию из utils
        add_sound_with_repeats(scene, obj, sound, entry)

        self.report({'INFO'}, f"Звук '{sound.name}' привязан к объекту '{obj.name}'!")
        return {'FINISHED'}



class SOUND_SYNTH_OT_RemoveSound(bpy.types.Operator):
    bl_idname = "sound_synth.remove_sound"
    bl_label = "Удалить звук"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        scene = context.scene

        if not obj or not obj.sound_synth_attached_sounds:
            self.report({'WARNING'}, "Нет звука для удаления.")
            return {'CANCELLED'}

        # Получаем привязанный звук
        sound_item = obj.sound_synth_attached_sounds[0]
        sound_name = sound_item.sound_name
        sound = bpy.data.sounds.get(sound_name)

        # Если звук не найден, очищаем привязку и выходим
        if not sound:
            obj.sound_synth_attached_sounds.clear()
            self.report({'WARNING'}, f"Звук '{sound_name}' не найден.")
            return {'CANCELLED'}

        # Удаляем все дорожки этого звука из VSE
        if scene.sequence_editor:
            sequences_to_remove = [
                seq for seq in scene.sequence_editor.sequences_all
                if seq.type == 'SOUND' and seq.sound == sound
            ]
            for seq in sequences_to_remove:
                scene.sequence_editor.sequences.remove(seq)

        # Очищаем привязку звука к объекту
        obj.sound_synth_attached_sounds.clear()

        # Опционально: удалить сам звук из данных Blender
        bpy.data.sounds.remove(sound)

        self.report({'INFO'}, f"Звук '{sound_name}' удалён.")
        return {'FINISHED'}


class SOUND_SYNTH_OT_UpdateSound(bpy.types.Operator):
    bl_idname = "sound_synth.update_sound"
    bl_label = "Обновить настройки звука"

    def execute(self, context):
        obj = context.object
        scene = context.scene
        if not obj or not obj.sound_synth_attached_sounds:
            self.report({'WARNING'}, "Нет звука для обновления.")
            return {'CANCELLED'}
        entry = obj.sound_synth_attached_sounds[0]
        entry.frame_start = scene.freesound_start_frame
        entry.frame_end = scene.freesound_end_frame
        entry.repeat_frames = scene.freesound_repeat_frames
        entry.spectral_mod = scene.freesound_spectral_mod
        entry.added_frames = ""  # Сбросить при обновлении настроек

        self.report({'INFO'}, f"Настройки звука обновлены для объекта '{obj.name}'.")
        return {'FINISHED'}


class SOUND_SYNTH_OT_FSearch(bpy.types.Operator):
    bl_idname = "sound_synth.fsearch"
    bl_label = "Поиск звука на Freesound"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        print("[DEBUG] SOUND_SYNTH_OT_FSearch.execute() вызван.")
        if database.DB_MANAGER is None:
            self.report({'ERROR'}, "База данных не инициализирована!")
            print("[DEBUG] Ошибка: database.DB_MANAGER равен None!")
            return {'CANCELLED'}

        scene = context.scene
        api_key = scene.freesound_api_key
        query = scene.freesound_query
        if not api_key:
            self.report({'ERROR'}, "Укажите ваш API ключ Freesound!")
            return {'CANCELLED'}

        url = "https://freesound.org/apiv2/search/text/"
        params = {
            "query": query,
            "fields": "id,name,previews",
            "page_size": 10
        }
        headers = {"Authorization": f"Token {api_key}"}
        try:
            response = requests.get(url, params=params, headers=headers)
            print("[DEBUG] Запрос выполнен. Код ответа:", response.status_code)
            if response.status_code != 200:
                self.report({'ERROR'}, f"Ошибка поиска: {response.status_code}")
                return {'CANCELLED'}
            data = response.json()
            results = data.get("results", [])
            scene.freesound_results.clear()

            for item in results:
                sound_id = str(item.get("id"))
                name = item.get("name", "Без названия")
                previews = item.get("previews", {})
                preview_url = previews.get("preview-hq-mp3", "")
                entry = scene.freesound_results.add()
                entry.sound_id = sound_id
                entry.name = name
                entry.preview_url = preview_url

                database.DB_MANAGER.add_freesound_result(sound_id, name, preview_url)

            database.DB_MANAGER.add_search_history(query)

            if not scene.freesound_results:
                self.report({'WARNING'}, "Ничего не найдено.")
            else:
                self.report({'INFO'}, f"Найдено {len(scene.freesound_results)} результатов.")
            return {'FINISHED'}
        except Exception as e:
            print("[DEBUG] Исключение в SOUND_SYNTH_OT_FSearch:", e)
            self.report({'ERROR'}, f"Ошибка: {e}")
            return {'CANCELLED'}


class SOUND_SYNTH_OT_FPreview(bpy.types.Operator):
    bl_idname = "sound_synth.fpreview"
    bl_label = "Предпрослушать звук"

    def execute(self, context):
        scene = context.scene
        index = scene.freesound_index
        if index < 0 or index >= len(scene.freesound_results):
            self.report({'WARNING'}, "Выберите результат.")
            return {'CANCELLED'}
        result = scene.freesound_results[index]
        if result.preview_url:
            webbrowser.open(result.preview_url)
            self.report({'INFO'}, f"Предпрослушивание звука '{result.name}'")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, "URL предпрослушивания не найден.")
            return {'CANCELLED'}


class SOUND_SYNTH_OT_FAdd(bpy.types.Operator):
    bl_idname = "sound_synth.fadd"
    bl_label = "Добавить звук из Freesound"

    def execute(self, context):
        scene = context.scene
        obj = context.object
        if not obj:
            self.report({'WARNING'}, "Нет активного объекта!")
            return {'CANCELLED'}
        index = scene.freesound_index
        if index < 0 or index >= len(scene.freesound_results):
            self.report({'WARNING'}, "Выберите результат.")
            return {'CANCELLED'}
        result = scene.freesound_results[index]
        if not result.preview_url:
            self.report({'ERROR'}, "URL для загрузки не найден.")
            return {'CANCELLED'}
        try:
            response = requests.get(result.preview_url, stream=True)
            if response.status_code != 200:
                self.report({'ERROR'}, "Не удалось загрузить звук.")
                return {'CANCELLED'}
            tmp_dir = tempfile.gettempdir()
            tmp_filepath = os.path.join(tmp_dir, f"freesound_{result.sound_id}.mp3")
            with open(tmp_filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            sound = bpy.data.sounds.load(tmp_filepath, check_existing=True)

            if any(s.name == sound.name for s in scene.sound_synth_sounds):
                self.report({'WARNING'}, f"Звук '{sound.name}' уже загружен!")
                return {'CANCELLED'}

            new_sound = scene.sound_synth_sounds.add()
            new_sound.name = sound.name
            scene.sound_synth_selected = sound.name

            obj.sound_synth_attached_sounds.clear()
            entry = obj.sound_synth_attached_sounds.add()
            entry.sound_name = sound.name
            entry.frame_start = scene.freesound_start_frame
            entry.frame_end = scene.freesound_end_frame
            entry.repeat_frames = scene.freesound_repeat_frames
            entry.spectral_mod = scene.freesound_spectral_mod

            self.report({'INFO'}, f"Звук '{sound.name}' добавлен и привязан к объекту '{obj.name}'!")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Ошибка при добавлении звука: {e}")
            return {'CANCELLED'}


class SOUND_SYNTH_OT_ApplyDSPChain(bpy.types.Operator):
    bl_idname = "sound_synth.apply_dsp_chain"
    bl_label = "Применить DSP эффекты"
    bl_options = {'REGISTER', 'UNDO'}

    reverb_delay: bpy.props.IntProperty(name="Reverb задержка (мс)", default=300, min=10, max=1000)  # Было 100
    reverb_decay: bpy.props.IntProperty(name="Reverb затухание (dB)", default=12, min=0, max=20)  # Было 6
    delay_delay: bpy.props.IntProperty(name="Delay задержка (мс)", default=500, min=10, max=2000)  # Было 300
    delay_decay: bpy.props.IntProperty(name="Delay затухание (dB)", default=6, min=0, max=20)  # Было 3
    delay_reps: bpy.props.IntProperty(name="Повторы", default=2, min=0, max=10)
    low_gain: bpy.props.FloatProperty(name="Low Gain (dB)", default=0.0, min=-10.0, max=10.0)
    high_gain: bpy.props.FloatProperty(name="High Gain (dB)", default=0.0, min=-10.0, max=10.0)
    pitch_shift: bpy.props.IntProperty(name="Pitch Shift (полутона)", default=0, min=-12, max=12)

    def execute(self, context):
        scene = context.scene
        selected_sound_name = scene.sound_synth_selected
        if not selected_sound_name:
            self.report({'WARNING'}, "Сначала выберите звук!")
            return {'CANCELLED'}

        sound = bpy.data.sounds.get(selected_sound_name)
        if not sound:
            self.report({'ERROR'}, "Звук не найден в bpy.data.sounds!")
            return {'CANCELLED'}

        input_filepath = sound.filepath
        if not os.path.exists(input_filepath):
            self.report({'ERROR'}, f"Файл звука '{input_filepath}' не найден!")
            return {'CANCELLED'}

        tmp_dir = tempfile.gettempdir()
        output_filepath = os.path.join(tmp_dir, f"dsp_processed_{os.path.basename(input_filepath)}")
        self.report({'INFO'}, f"Обработка звука начинается. Исходник: {input_filepath}")

        effects = [
            lambda audio: dsp.apply_reverb(audio, delay_ms=self.reverb_delay, decay_dB=self.reverb_decay),
            lambda audio: dsp.apply_delay(audio, delay_ms=self.delay_delay, decay_dB=self.delay_decay,
                                          repetitions=self.delay_reps),
            lambda audio: dsp.apply_eq(audio, low_gain=self.low_gain, high_gain=self.high_gain),
            lambda audio: dsp.apply_pitch_shift(audio, semitones=self.pitch_shift)
        ]

        processed_path = dsp.process_audio(input_filepath, output_filepath, effects)
        if not processed_path:
            self.report({'ERROR'}, "Ошибка обработки аудио!")
            return {'CANCELLED'}

        try:
            processed_sound = bpy.data.sounds.load(processed_path, check_existing=True)
        except Exception as e:
            self.report({'ERROR'}, f"Ошибка загрузки обработанного звука: {e}")
            return {'CANCELLED'}

            # Обновляем привязанный звук у объекта
            obj = context.object
            if obj and obj.sound_synth_attached_sounds:
                entry = obj.sound_synth_attached_sounds[0]
                entry.sound_name = processed_sound.name  # <-- Ключевое изменение
                scene.sequence_editor.sequences_all.update()

        scene.sound_synth_selected = processed_sound.name
        self.report({'INFO'}, f"Обработка завершена. Новый звук: {processed_sound.name}")
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)


# Обработчик изменения кадра, который обновляет громкость звука в зависимости от расстояния
def dynamic_volume_handler(scene):
    cam = scene.camera
    if not cam:
        print("[Sound Synth] Нет камеры на сцене.")
        return

    # Если Sequence Editor отсутствует – создаём его
    if not scene.sequence_editor:
        print("[Sound Synth] Sequence Editor отсутствует, создаю...")
        scene.sequence_editor_create()
        if not scene.sequence_editor:
            print("[Sound Synth] Не удалось создать Sequence Editor!")
            return

    # Текущий кадр анимации
    current_frame = scene.frame_current
    # Получаем настройки затухания из пользовательских свойств
    auto_attenuation = scene.sound_synth_attenuation_enable
    attenuation_factor = scene.sound_synth_attenuation_factor

    for obj in scene.objects:
        # Если у объекта нет звуков или список пуст – пропускаем его
        if not hasattr(obj, "sound_synth_attached_sounds") or not obj.sound_synth_attached_sounds:
            continue

        entry = obj.sound_synth_attached_sounds[0]
        sound = bpy.data.sounds.get(entry.sound_name)
        if not sound:
            print(f"[Sound Synth] ❌ Звук '{entry.sound_name}' не найден")
            continue

        if not os.path.exists(sound.filepath):
            print(f"[Sound Synth] ❌ Файл звука '{sound.filepath}' не найден!")
            continue

        # Вычисляем расстояние от объекта до камеры
        distance = (obj.location - cam.location).length

        # Если включено автоматическое затухание – рассчитываем громкость по формуле
        # volume = max(0.0, min(1.0, 1 - distance / attenuation_factor))
        # Если функция выключена – громкость всегда равна 1.0
        if auto_attenuation:
            volume = max(0.0, min(1.0, 1 - distance / attenuation_factor))
        else:
            volume = 1.0
            # Всегда применяем spectral_mod, даже если затухание выключено
            volume *= entry.spectral_mod  # <-- Убрана проверка hasattr()

        # Если у звука есть дополнительный модификатор, например, spectral_mod, применим его
        if hasattr(entry, "spectral_mod"):
            volume *= entry.spectral_mod

        # Ищем звуковую дорожку, соответствующую звуку, в Sequence Editor
        seq = None
        for s in scene.sequence_editor.sequences_all:
            if s.type == 'SOUND' and s.sound == sound:
                seq = s
                break

        if seq:
            seq.volume = volume
            print(f"[Sound Synth] Обновлена громкость '{sound.name}': distance = {distance:.2f}, volume = {volume:.2f}")
        else:
            print(f"[Sound Synth] Звуковая дорожка для '{sound.name}' не найдена.")


# Оператор для включения динамического изменения громкости (добавляет обработчик)
class SOUND_SYNTH_OT_EnableDynamicVolume(bpy.types.Operator):
    """Включает динамическое изменение громкости звука при анимации объекта (отдалении/приближении к камере)"""
    bl_idname = "sound_synth.enable_dynamic_volume"
    bl_label = "Включить динамическое изменение громкости"

    def execute(self, context):
        # Проверяем, если обработчик уже есть – ничего не делаем
        if dynamic_volume_handler not in bpy.app.handlers.frame_change_post:
            bpy.app.handlers.frame_change_post.append(dynamic_volume_handler)
            self.report({'INFO'}, "Динамическое изменение громкости включено.")
            print("[Sound Synth] dynamic_volume_handler добавлен.")
        else:
            self.report({'INFO'}, "Динамическое изменение громкости уже включено.")
        return {'FINISHED'}


# Оператор для отключения динамического изменения громкости (удаляет обработчик)
class SOUND_SYNTH_OT_DisableDynamicVolume(bpy.types.Operator):
    """Отключает динамическое изменение громкости звука (удаляет обработчик кадра)"""
    bl_idname = "sound_synth.disable_dynamic_volume"
    bl_label = "Отключить динамическое изменение громкости"

    def execute(self, context):
        if dynamic_volume_handler in bpy.app.handlers.frame_change_post:
            bpy.app.handlers.frame_change_post.remove(dynamic_volume_handler)
            self.report({'INFO'}, "Динамическое изменение громкости отключено.")
            print("[Sound Synth] dynamic_volume_handler удалён.")
        else:
            self.report({'INFO'}, "Динамическое изменение громкости уже отключено.")
        return {'FINISHED'}


import numpy as np
from pydub import AudioSegment
import tempfile
import os


class SOUND_SYNTH_OT_ProcessSound(bpy.types.Operator):
    bl_idname = "sound_synth.process_sound"
    bl_label = "Обработать звук с затуханием"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        scene = context.scene

        if not obj or not obj.sound_synth_attached_sounds:
            self.report({'ERROR'}, "Сначала привяжите звук к объекту!")
            return {'CANCELLED'}

        entry = obj.sound_synth_attached_sounds[0]
        sound = bpy.data.sounds.get(entry.sound_name)
        if not sound or not os.path.exists(sound.filepath):
            self.report({'ERROR'}, "Звуковой файл не найден!")
            return {'CANCELLED'}

        # Загрузка исходного аудио
        audio = AudioSegment.from_file(sound.filepath)

        # Расчёт параметров
        fps = scene.render.fps
        duration_frames = entry.frame_end - entry.frame_start
        duration_seconds = duration_frames / fps

        # Создаём массив громкости для каждого кадра
        volume_profile = self._calculate_volume_profile(obj, scene, duration_frames)

        # Применяем затухание
        processed_audio = self._apply_volume(audio, volume_profile, fps)

        # Сохраняем временный файл
        tmp_dir = tempfile.gettempdir()
        output_path = os.path.join(tmp_dir, f"processed_{os.path.basename(sound.filepath)}")
        processed_audio.export(output_path, format="wav")

        # Загружаем обработанный звук в Blender
        processed_sound = bpy.data.sounds.load(output_path)
        entry.sound_name = processed_sound.name

        self.report({'INFO'}, "Звук обработан!")
        return {'FINISHED'}

    def _calculate_volume_profile(self, obj, scene, duration_frames):
        """Возвращает массив громкости для каждого кадра [0..1]."""
        cam = scene.camera
        volume_profile = np.ones(duration_frames)

        for frame in range(duration_frames):
            # Рассчитываем позицию объекта на текущем кадре
            scene.frame_set(frame + scene.frame_start)
            distance = (obj.location - cam.location).length
            volume = max(0.1, 1 - distance / scene.sound_synth_attenuation_factor)
            volume_profile[frame] = volume

        return volume_profile

    def _apply_volume(self, audio, volume_profile, fps):
        """Применяет плавное изменение громкости к аудио."""
        audio = audio.set_frame_rate(int(fps * 1000))  # Для точности
        return audio.apply_gain([v * 100 - 100 for v in volume_profile])