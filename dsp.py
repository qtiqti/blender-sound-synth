from pydub import AudioSegment
import tempfile

def apply_reverb(audio, delay_ms=100, decay_dB=6):
    """
    Применяет эффект реверберации:
    - Создаёт эхо: создаёт тихий сигнал заданной длительности,
      затем накладывает на оригинал ослабленный звук.
    """
    # Создаем копию аудио с ослаблением для эха
    echo = AudioSegment.silent(duration=delay_ms) + audio.apply_gain(-decay_dB)
    # Накладываем эхо на оригинал
    processed = audio.overlay(echo)
    return processed


def apply_delay(audio, delay_ms=300, decay_dB=3, repetitions=2):
    """
    Применяет эффект задержки (delay) с заданным числом повторов.
    Каждый повтор начинается с увеличенной задержкой, а громкость повторов уменьшается.
    """
    output = audio
    for i in range(1, repetitions + 1):
        # Задержка увеличивается на i * delay_ms, а ослабление – на i * decay_dB
        delayed = AudioSegment.silent(duration=delay_ms * i) + audio.apply_gain(-decay_dB * i)
        output = output.overlay(delayed)
    return output


def apply_eq(audio, low_gain=0.0, high_gain=0.0):
    """
    Применяет простой эквалайзер:
    - Для низких частот используется low_pass_filter (до 200 Hz)
    - Для высоких частот используется high_pass_filter (от 2000 Hz)
    Затем корректируются уровни громкости полученных фрагментов и накладываются на оригинал.
    """
    # Извлекаем "низкие" компоненты и усиливаем/ослабляем их
    lows = audio.low_pass_filter(200).apply_gain(low_gain)
    # Извлекаем "высокие" компоненты и корректируем их
    highs = audio.high_pass_filter(2000).apply_gain(high_gain)
    # Объединяем оригинал с обработанными частями
    processed = audio.overlay(lows).overlay(highs)
    return processed


def apply_pitch_shift(audio, semitones=0):
    """
    Применяет сдвиг тональности (pitch shift) путём изменения frame_rate.
    При этом длительность аудио сохраняется за счет последующей корректировки.
    """
    if semitones == 0:
        return audio
    new_rate = int(audio.frame_rate * (2 ** (semitones / 12.0)))
    shifted = audio._spawn(audio.raw_data, overrides={"frame_rate": new_rate})
    # Возвращаем аудио с исходным frame_rate, чтобы сохранить длительность
    return shifted.set_frame_rate(audio.frame_rate)


def apply_lowpass_filter(audio, cutoff_frequency=3000):
    """
    Применяет низкочастотную фильтрацию методом дискретного преобразования Фурье (ДПФ).

    Данный метод позволяет удалить высокочастотные компоненты сигнала, сохранены
    только низкочастотные составляющие. Пусть x[n] - входной сигнал, представленный в виде ряда длины N.
    Дискретное преобразование Фурье задаётся выражением:

        X[k] = sum(x[n] * exp(-j*2*pi*k*n/N)), k=0,..., N-1.

    Формируется булева маска, оставляющая компоненты спектра, удовлетворяющие условию |f| < cutoff_frequency.
    После умножения спектра на маску выполняется обратное преобразование Фурье для получения отфильтрованного временного сигнала.
    """
    import numpy as np

    # Преобразуем аудиофайл в массив сэмплов
    samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
    N = len(samples)

    # Вычисляем ДПФ сигнала
    spectrum = np.fft.fft(samples)
    # Определяем соответствующие частоты для каждого сэмпла
    freqs = np.fft.fftfreq(N, d=1 / audio.frame_rate)
    # Создаем маску, оставляя только компоненты с абсолютной частотой ниже cutoff_frequency
    mask = np.abs(freqs) < cutoff_frequency
    filtered_spectrum = spectrum * mask

    # Обратное преобразование для получения временного сигнала
    filtered_samples = np.fft.ifft(filtered_spectrum).real
    filtered_samples = np.int16(filtered_samples)

    # Создаем новый AudioSegment с отфильтрованными данными
    filtered_audio = audio._spawn(filtered_samples.tobytes())
    return filtered_audio


def process_audio(input_filepath, output_filepath, effects_list):
    """
    Загружает аудиофайл по пути input_filepath, последовательно применяет эффекты из списка effects_list,
    где каждый элемент является функцией, принимающей и возвращающей объект AudioSegment.
    Результат экспортируется в формате mp3 по пути output_filepath.
    """
    try:
        audio = AudioSegment.from_file(input_filepath)
    except Exception as e:
        print("Ошибка загрузки аудио:", e)
        return None

    # Применяем эффекты последовательно
    for effect in effects_list:
        audio = effect(audio)

    try:
        audio.export(output_filepath, format="mp3")
    except Exception as e:
        print("Ошибка экспорта аудио:", e)
        return None

    print(f"[DEBUG] Аудио сохранено по пути: {output_filepath}")
    return output_filepath
