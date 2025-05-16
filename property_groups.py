import bpy


class SoundItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Sound Name")
    min_distance: bpy.props.FloatProperty(
        name="Минимальное расстояние",
        default=5.0,
        min=0.1
    )
    max_distance: bpy.props.FloatProperty(
        name="Максимальное расстояние",
        default=50.0,
        min=1.0
    )


class ObjectSoundItem(bpy.types.PropertyGroup):
    sound_name: bpy.props.StringProperty(name="Sound Name")
    frame_start: bpy.props.IntProperty(name="Начальный кадр", default=1)
    frame_end: bpy.props.IntProperty(name="Конечный кадр", default=250)
    repeat_frames: bpy.props.StringProperty()
    repeat_interval: bpy.props.IntProperty()
    added_frames: bpy.props.StringProperty(default="")  # Хранит кадры в формате "1,50,100"
    repeat_frames: bpy.props.StringProperty(
        name="Повторы (кадры)",
        default="",
        description="Введите номера кадров через запятую для повторного воспроизведения"
    )
    spectral_mod: bpy.props.FloatProperty(
        name="Spectral Mod",
        default=1.0,
        min=0.0,
        max=2.0,
        description="Коэффициент для обработки звука"
    )


class FreesoundSearchResult(bpy.types.PropertyGroup):
    sound_id: bpy.props.StringProperty(name="Sound ID")
    name: bpy.props.StringProperty(name="Name")
    preview_url: bpy.props.StringProperty(name="Preview URL")
