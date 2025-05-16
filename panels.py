import bpy
import tempfile

class SOUND_SYNTH_UL_FreesoundResults(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="")


class SOUND_SYNTH_PT_LocalLoadPanel(bpy.types.Panel):
    bl_label = "Локальная загрузка звука"
    bl_idname = "SOUND_SYNTH_PT_local_load"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sound Synth'
    bl_order = 0  # Появится выше Freesound-панели

    def draw(self, context):
        layout = self.layout
        layout.operator("sound_synth.load_sound", text="Загрузить звук с компьютера", icon="FILE_SOUND")


class SOUND_SYNTH_PT_FreesoundPanel(bpy.types.Panel):
    bl_label = "Sound Synth"
    bl_idname = "SOUND_SYNTH_PT_freesound"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sound Synth'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # --- Секция 1: Поиск звука через Freesound API ---
        box = layout.box()
        box.label(text="Поиск звука на Freesound", icon='FILE_FOLDER')
        box.prop(scene, "freesound_api_key", text="API Key")
        box.prop(scene, "freesound_query", text="Запрос")
        box.operator("sound_synth.fsearch", text="Найти звук")

        if scene.freesound_results:
            box.label(text="Результаты:")
            box.template_list("SOUND_SYNTH_UL_FreesoundResults", "", scene, "freesound_results",
                              scene, "freesound_index", rows=3)
            row = box.row(align=True)
            row.operator("sound_synth.fpreview", text="Предпрослушать")
            row.operator("sound_synth.fadd", text="Добавить звук")

        # --- Секция 2: Настройки добавленного звука ---
        if scene.sound_synth_selected:
            box2 = layout.box()
            box2.label(text="Настройки звука", icon='SOUND')
            box2.prop(scene, "sound_synth_selected", text="Звук")
            box2.prop(scene, "freesound_start_frame", text="Начальный кадр")
            box2.prop(scene, "freesound_end_frame", text="Конечный кадр")
            box2.prop(scene, "freesound_repeat_frames", text="Повторы (кадры)")
            box2.prop(scene, "freesound_spectral_mod", text="Громкость")
            box2.prop(scene, "sound_synth_attenuation_enable", text="Автоматическое затухание")
            if scene.sound_synth_attenuation_enable:
                box2.prop(scene, "sound_synth_attenuation_factor", text="Чувствительность затухания")
            # if scene.sound_synth_attenuation_enable:
            #     layout.operator("sound_synth.process_sound", text="Препроцессинг звука")
            row2 = box2.row(align=True)
            row2.operator("sound_synth.attach_sound", text="Привязать")
            row2.operator("sound_synth.update_sound", text="Обновить настройки")
            # row2.operator("sound_synth.remove_sound", text="Удалить", icon='TRASH')


# class SOUND_SYNTH_PT_DynamicVolumePanel(bpy.types.Panel):
#     bl_label = "Динамическое изменение громкости"
#     bl_idname = "SOUND_SYNTH_PT_dynamic_volume"
#     bl_space_type = 'VIEW_3D'
#     bl_region_type = 'UI'
#     bl_category = 'Sound Synth'
#
#     def draw(self, context):
#         layout = self.layout
#         scene = context.scene
#
#         # Чекбокс для автоматического затухания
#         layout.prop(scene, "sound_synth_attenuation_enable", text="Автоматическое затухание")
#         if scene.sound_synth_attenuation_enable:
#             layout.prop(scene, "sound_synth_attenuation_factor", text="Чувствительность затухания")
#
#         # Кнопки включения/отключения динамического изменения громкости
#         row = layout.row(align=True)
#         row.operator("sound_synth.enable_dynamic_volume", text="Включить динамику")
#         row.operator("sound_synth.disable_dynamic_volume", text="Отключить динамику")

from . import dsp
# Оператор для применения эффектов
class SOUND_SYNTH_OT_ApplyEffects(bpy.types.Operator):
    bl_idname = "sound_synth.apply_effects"
    bl_label = "Применить эффекты"
    bl_options = {'REGISTER', 'UNDO'}

    # Свойства для эффектов
    reverb_enable: bpy.props.BoolProperty(name="Реверберация", default=False)
    reverb_delay: bpy.props.IntProperty(name="Задержка реверба (мс)", default=100, min=10, max=1000)
    reverb_decay: bpy.props.IntProperty(name="Затухание реверба (dB)", default=6, min=0, max=20)

    delay_enable: bpy.props.BoolProperty(name="Задержка", default=False)
    delay_time: bpy.props.IntProperty(name="Время задержки (мс)", default=300, min=10, max=2000)
    delay_repeats: bpy.props.IntProperty(name="Количество повторов", default=2, min=1, max=10)

    eq_enable: bpy.props.BoolProperty(name="Эквалайзер", default=False)
    low_gain: bpy.props.FloatProperty(name="Низкие частоты (dB)", default=0.0, min=-20.0, max=20.0)
    high_gain: bpy.props.FloatProperty(name="Высокие частоты (dB)", default=0.0, min=-20.0, max=20.0)

    pitch_enable: bpy.props.BoolProperty(name="Сдвиг тона", default=False)
    pitch_shift: bpy.props.IntProperty(name="Сдвиг (полутонов)", default=0, min=-12, max=12)

    def execute(self, context):
        scene = context.scene
        selected_sound = scene.sound_synth_selected

        if not selected_sound:
            self.report({'ERROR'}, "Сначала выберите звук!")
            return {'CANCELLED'}

        sound = bpy.data.sounds.get(selected_sound)
        if not sound or not sound.filepath:
            self.report({'ERROR'}, "Звуковой файл не найден!")
            return {'CANCELLED'}

        # Создаем список эффектов
        effects = []

        if self.reverb_enable:
            effects.append(
                lambda audio: dsp.apply_reverb(
                    audio,
                    delay_ms=self.reverb_delay,
                    decay_dB=self.reverb_decay
                )
            )

        if self.delay_enable:
            effects.append(
                lambda audio: dsp.apply_delay(
                    audio,
                    delay_ms=self.delay_time,
                    repetitions=self.delay_repeats
                )
            )

        if self.eq_enable:
            effects.append(
                lambda audio: dsp.apply_eq(
                    audio,
                    low_gain=self.low_gain,
                    high_gain=self.high_gain
                )
            )

        if self.pitch_enable:
            effects.append(
                lambda audio: dsp.apply_pitch_shift(
                    audio,
                    semitones=self.pitch_shift
                )
            )

        # Обработка аудио
        output_path = dsp.process_audio(
            input_filepath=sound.filepath,
            output_filepath=tempfile.mktemp(suffix=".mp3"),
            effects_list=effects
        )

        if output_path:
            # Загружаем обработанный звук
            new_sound = bpy.data.sounds.load(output_path)
            scene.sound_synth_selected = new_sound.name
            self.report({'INFO'}, "Эффекты успешно применены!")
        else:
            self.report({'ERROR'}, "Ошибка обработки аудио!")

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


# Панель для эффектов
class SOUND_SYNTH_PT_EffectsPanel(bpy.types.Panel):
    bl_label = "Аудио Эффекты"
    bl_idname = "SOUND_SYNTH_PT_effects"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Sound Synth'

    def draw(self, context):
        layout = self.layout
        operator = layout.operator("sound_synth.apply_effects")

        # Реверберация
        box = layout.box()
        box.prop(operator, "reverb_enable", text="Реверберация")
        if operator.reverb_enable:
            box.prop(operator, "reverb_delay")
            box.prop(operator, "reverb_decay")

        # Задержка
        box = layout.box()
        box.prop(operator, "delay_enable", text="Задержка")
        if operator.delay_enable:
            box.prop(operator, "delay_time")
            box.prop(operator, "delay_repeats")

        # Эквалайзер
        box = layout.box()
        box.prop(operator, "eq_enable", text="Эквалайзер")
        if operator.eq_enable:
            box.prop(operator, "low_gain")
            box.prop(operator, "high_gain")

        # Сдвиг тона
        box = layout.box()
        box.prop(operator, "pitch_enable", text="Сдвиг тона")
        if operator.pitch_enable:
            box.prop(operator, "pitch_shift")