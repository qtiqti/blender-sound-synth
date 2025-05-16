bl_info = {
    "name": "Sound Synthesizer",
    "author": "Соня",
    "version": (1, 0),
    "blender": (4, 2, 0),
    "location": "Properties > Sound Synth",
    "description": "Аддон для синтеза звуковых эффектов в Blender",
    "category": "Sound",
}

import bpy
class SOUND_SYNTH_OT_LoadSound(bpy.types.Operator):
    """Загрузка звука в сцену"""
    bl_idname = "sound_synth.load_sound"
    bl_label = "Загрузить звук"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        # Загружаем звук
        sound = bpy.data.sounds.load(self.filepath, check_existing=True)

        # Добавляем звук в список
        context.scene.sound_synth_sounds.append(sound.name)
        self.report({'INFO'}, f"Звук {sound.name} загружен!")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

# Панель интерфейса
class SOUND_SYNTH_PT_MainPanel(bpy.types.Panel):
    """Главная панель аддона"""
    bl_label = "Sound Synthesizer"
    bl_idname = "SOUND_SYNTH_PT_main"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        layout.operator("sound_synth.load_sound", text="Загрузить звук")
        layout.label(text="Выбрать звук:")
        layout.prop(context.scene, "sound_synth_selected", text="")

def register():
    bpy.utils.register_class(SOUND_SYNTH_OT_LoadSound)
    bpy.utils.register_class(SOUND_SYNTH_PT_MainPanel)
    bpy.types.Scene.sound_synth_sounds = bpy.props.CollectionProperty(type=bpy.types.PropertyGroup)
    bpy.types.Scene.sound_synth_selected = bpy.props.StringProperty()

def unregister():
    bpy.utils.unregister_class(SOUND_SYNTH_OT_LoadSound)
    bpy.utils.unregister_class(SOUND_SYNTH_PT_MainPanel)
    del bpy.types.Scene.sound_synth_sounds
    del bpy.types.Scene.sound_synth_selected

if __name__ == "__main__":
    register()