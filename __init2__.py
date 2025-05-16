import bpy
import math

bl_info = {
    "name": "Sound Synthesizer",
    "author": "Соня",
    "version": (1, 9),
    "blender": (4, 2, 0),
    "location": "Properties > Object",
    "description": "Автоматическое воспроизведение звуков в Blender",
    "category": "Sound",
}


# === ДАННЫЕ ===

class SoundItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Sound Name")


class ObjectSoundItem(bpy.types.PropertyGroup):
    sound_name: bpy.props.StringProperty(name="Sound Name")
    frame_start: bpy.props.IntProperty(name="Start Frame", default=1)
    frame_end: bpy.props.IntProperty(name="End Frame", default=250)


# === ОПЕРАТОРЫ ===

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
    bl_label = "Привязать звук"

    def execute(self, context):
        obj = context.object
        scene = context.scene
        if not obj:
            self.report({'WARNING'}, "Нет активного объекта!")
            return {'CANCELLED'}

        selected_sound = scene.sound_synth_selected
        if not selected_sound:
            self.report({'WARNING'}, "Выберите звук!")
            return {'CANCELLED'}

        sound = bpy.data.sounds.get(selected_sound)
        if not sound:
            self.report({'ERROR'}, f"Звук '{selected_sound}' не найден!")
            return {'CANCELLED'}

        # Очищаем предыдущую привязку
        obj.sound_synth_attached_sounds.clear()

        entry = obj.sound_synth_attached_sounds.add()
        entry.sound_name = sound.name
        entry.frame_start = scene.sound_synth_start_frame
        entry.frame_end = scene.sound_synth_end_frame

        self.report({'INFO'}, f"Звук '{sound.name}' привязан к объекту '{obj.name}'!")
        return {'FINISHED'}


class SOUND_SYNTH_OT_RemoveSound(bpy.types.Operator):
    bl_idname = "sound_synth.remove_sound"
    bl_label = "Удалить звук"

    def execute(self, context):
        obj = context.object
        scene = context.scene
        if not obj or not obj.sound_synth_attached_sounds:
            self.report({'WARNING'}, "Нет звука для удаления.")
            return {'CANCELLED'}

        sound_name = obj.sound_synth_attached_sounds[0].sound_name

        if scene.sequence_editor:
            for seq in list(scene.sequence_editor.sequences_all):
                if seq.type == 'SOUND' and seq.sound.name == sound_name:
                    scene.sequence_editor.sequences.remove(seq)

        obj.sound_synth_attached_sounds.clear()
        self.report({'INFO'}, f"Звук '{sound_name}' удалён.")
        return {'FINISHED'}


class SOUND_SYNTH_OT_UpdateSound(bpy.types.Operator):
    bl_idname = "sound_synth.update_sound"
    bl_label = "Обновить интервал звука"

    def execute(self, context):
        obj = context.object
        scene = context.scene
        if not obj or not obj.sound_synth_attached_sounds:
            self.report({'WARNING'}, "Нет звука для обновления.")
            return {'CANCELLED'}

        entry = obj.sound_synth_attached_sounds[0]
        entry.frame_start = scene.sound_synth_start_frame
        entry.frame_end = scene.sound_synth_end_frame

        self.report({'INFO'}, f"Интервал звука обновлён для объекта '{obj.name}'.")
        return {'FINISHED'}


# === ОБРАБОТЧИК ===
# def sound_playback(scene):
#     cam = scene.camera
#     if not cam:
#         print("[Sound Synth] Нет камеры на сцене.")
#         return
#
#     if not scene.sequence_editor:
#         print("[Sound Synth] Sequence Editor отсутствует, создаю...")
#         scene.sequence_editor_create()
#
#     current_frame = scene.frame_current
#     print(f"[Sound Synth] Текущий кадр: {current_frame}")
#
#     for obj in scene.objects:
#         if not hasattr(obj, "sound_synth_attached_sounds"):
#             continue
#         if not obj.sound_synth_attached_sounds:
#             continue
#
#         entry = obj.sound_synth_attached_sounds[0]
#         sound = bpy.data.sounds.get(entry.sound_name)
#
#         print(f"[Sound Synth] Объект: {obj.name}, Звук: {entry.sound_name}")
#
#         if not sound:
#             print(f"[Sound Synth] ❌ Звук '{entry.sound_name}' не найден в bpy.data.sounds")
#             continue
#
#         distance = (obj.location - cam.location).length
#         volume = max(0.0, min(1.0, 1 - distance / 20.0))
#         print(f"[Sound Synth] Расстояние до камеры: {distance:.2f}, Громкость: {volume:.2f}")
#
#         existing_seq = next((seq for seq in scene.sequence_editor.sequences_all
#                              if seq.type == 'SOUND' and seq.sound.name == sound.name), None)
#
#         if not existing_seq:
#             try:
#                 print(f"[Sound Synth] Добавляю звук {sound.name} в VSE с {entry.frame_start} по {entry.frame_end}")
#                 seq = scene.sequence_editor.sequences.new_sound(
#                     name=sound.name,
#                     filepath=sound.filepath,
#                     channel=1,
#                     frame_start=entry.frame_start
#                 )
#                 seq.frame_final_end = entry.frame_end
#                 seq.volume = volume
#                 seq.sound = sound
#             except Exception as e:
#                 print(f"[Sound Synth] ❌ Ошибка создания звуковой дорожки: {e}")
#         else:
#             print(f"[Sound Synth] Обновляю существующую дорожку: {sound.name}")
#             existing_seq.frame_final_start = entry.frame_start
#             existing_seq.frame_final_end = entry.frame_end
#             existing_seq.volume = volume

def sound_playback(scene):
    cam = scene.camera
    if not cam:
        print("[Sound Synth] Нет камеры на сцене.")
        return

    # Создать Sequence Editor, если отсутствует
    if not scene.sequence_editor:
        scene.sequence_editor_create()

    current_frame = scene.frame_current

    for obj in scene.objects:
        # Пропустить объекты без привязанных звуков
        if not hasattr(obj, "sound_synth_attached_sounds") or not obj.sound_synth_attached_sounds:
            continue

        entry = obj.sound_synth_attached_sounds[0]
        sound = bpy.data.sounds.get(entry.sound_name)
        if not sound:
            print(f"[Sound Synth] ❌ Звук '{entry.sound_name}' не найден")
            continue

        # Если автоматическое затухание выключено, пропустить расчёт
        if not scene.sound_synth_attenuation_enable:
                continue

        # Рассчитать расстояние до камеры
        distance = (obj.location - cam.location).length
        # Формула затухания: 1 - (distance / коэффициент)
        volume = max(0.0, min(1.0, 1 - distance / scene.sound_synth_attenuation_factor))

        # Обновить громкость ВСЕХ дорожек этого звука
        for seq in scene.sequence_editor.sequences_all:
            if seq.type == 'SOUND' and seq.sound == sound:
                seq.volume = volume

        # Найти или создать звуковую дорожку
        existing_seq = next(
            (seq for seq in scene.sequence_editor.sequences_all
             if seq.type == 'SOUND' and seq.sound == sound),
            None
        )

        if existing_seq:
            # Обновить громкость существующей дорожки
            existing_seq.volume = volume
            print(f"[Sound Synth] Громкость обновлена: {volume:.2f}")
        else:
            # Создать новую дорожку
            try:
                seq = scene.sequence_editor.sequences.new_sound(
                    name=sound.name,
                    filepath=sound.filepath,
                    channel=1,
                    frame_start=entry.frame_start
                )
                seq.frame_final_end = entry.frame_end
                seq.volume = volume
                print(f"[Sound Synth] Добавлен звук: {sound.name}")
            except Exception as e:
                print(f"[Sound Synth] Ошибка: {e}")

# === ПАНЕЛЬ ===

class SOUND_SYNTH_PT_MainPanel(bpy.types.Panel):
    bl_label = "Sound Synthesizer"
    bl_idname = "SOUND_SYNTH_PT_main"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.operator("sound_synth.load_sound", text="Загрузить звук")

        if scene.sound_synth_sounds:
            layout.prop(scene, "sound_synth_selected", text="Выбранный звук")
            layout.prop(scene, "sound_synth_start_frame", text="Начальный кадр")
            layout.prop(scene, "sound_synth_end_frame", text="Конечный кадр")

            layout.operator("sound_synth.attach_sound", text="Привязать")
            layout.operator("sound_synth.update_sound", text="Обновить интервал")
            layout.operator("sound_synth.remove_sound", text="Удалить")
        else:
            layout.label(text="Нет загруженных звуков", icon='ERROR')


# === РЕГИСТРАЦИЯ ===

classes = (
    SoundItem, ObjectSoundItem,
    SOUND_SYNTH_OT_LoadSound, SOUND_SYNTH_OT_AttachSound,
    SOUND_SYNTH_OT_RemoveSound, SOUND_SYNTH_OT_UpdateSound,
    SOUND_SYNTH_PT_MainPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.sound_synth_sounds = bpy.props.CollectionProperty(type=SoundItem)
    bpy.types.Object.sound_synth_attached_sounds = bpy.props.CollectionProperty(type=ObjectSoundItem)
    bpy.types.Scene.sound_synth_selected = bpy.props.StringProperty(name="Выбранный звук")
    bpy.types.Scene.sound_synth_start_frame = bpy.props.IntProperty(name="Начальный кадр", default=1)
    bpy.types.Scene.sound_synth_end_frame = bpy.props.IntProperty(name="Конечный кадр", default=250)

    if sound_playback not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(sound_playback)


def unregister():
    if sound_playback in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(sound_playback)

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.sound_synth_sounds
    del bpy.types.Object.sound_synth_attached_sounds
    del bpy.types.Scene.sound_synth_selected
    del bpy.types.Scene.sound_synth_start_frame
    del bpy.types.Scene.sound_synth_end_frame


if __name__ == "__main__":
    register()
