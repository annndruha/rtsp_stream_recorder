import datetime
import os
import time
from pathlib import Path

import cv2

RTSP_URL = os.getenv('RTSP_URL')
SEGMENT_DURATION = int(os.getenv('SEGMENT_DURATION', '300'))

OUTPUT_DIR = Path('data')
OUTPUT_DIR.mkdir(exist_ok=True)

MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 5
FLUSH_INTERVAL = 5


def datetime_now_str():
    delta = datetime.timedelta(hours=3)
    tzone = datetime.timezone(delta)
    return datetime.datetime.strftime(datetime.datetime.now(tzone), '%H_%M_%S')


def get_video_writer(cap, filename):
    """Создает VideoWriter с параметрами из захваченного потока"""
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps == 0 or fps > 60:
        fps = 25

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Используем AVI с MJPEG - более устойчив к неожиданному закрытию
    # Можно также использовать 'XVID' или 'X264'
    fourcc = cv2.VideoWriter_fourcc(*'MJPG')

    # Сохраняем с расширением .avi для MJPEG
    avi_filename = str(filename).replace('.mp4', '.avi')

    writer = cv2.VideoWriter(avi_filename, fourcc, fps, (width, height))
    return writer, fps, avi_filename


def connect_to_stream():
    """Подключается к RTSP потоку с повторными попытками"""
    for attempt in range(MAX_RECONNECT_ATTEMPTS):
        print(f'Попытка подключения к {RTSP_URL} (попытка {attempt + 1}/{MAX_RECONNECT_ATTEMPTS})')

        cap = cv2.VideoCapture(RTSP_URL)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # Минимальный буфер для уменьшения задержки

        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                print('Успешное подключение к потоку')
                return cap

            print('Не удалось прочитать кадр')
            cap.release()

        if attempt < MAX_RECONNECT_ATTEMPTS - 1:
            print(f'Ожидание {RECONNECT_DELAY} секунд перед следующей попыткой...')
            time.sleep(RECONNECT_DELAY)

    return None


class FlushableVideoWriter:
    """Обертка над VideoWriter с периодической принудительной записью"""
    def __init__(self, writer, filename):
        self.writer = writer
        self.filename = filename
        self.last_flush = time.time()
        self.frame_count = 0

    def write(self, frame):
        self.writer.write(frame)
        self.frame_count += 1

        current_time = time.time()
        if current_time - self.last_flush >= FLUSH_INTERVAL:
            self.last_flush = current_time

    def release(self):
        self.writer.release()

    def is_opened(self):
        return self.writer.isOpened()


def record_stream():
    """Основная функция записи потока"""
    if not RTSP_URL:
        print('ОШИБКА: RTSP_URL не задан в переменных окружения')
        return

    print(f'URL: rtsp://***:***@{RTSP_URL.split("@")[1]}')
    print(f'Длительность сегмента: {SEGMENT_DURATION} секунд')
    print(f'Папка для сохранения: {OUTPUT_DIR}')

    cap = None
    writer = None
    segment_start_time = None
    frame_count = 0

    try:
        while True:
            if cap is None or not cap.isOpened():
                cap = connect_to_stream()
                if cap is None:
                    print('Не удалось подключиться к потоку. Завершение.')
                    break

                if writer is not None:
                    writer.release()
                    writer = None

                segment_start_time = None

            ret, frame = cap.read()

            if not ret:
                print('Потеря соединения или ошибка чтения кадра')
                if cap is not None:
                    cap.release()
                    cap = None
                if writer is not None:
                    writer.release()
                    writer = None
                time.sleep(RECONNECT_DELAY)
                continue

            current_time = time.time()

            # Создание нового сегмента
            if segment_start_time is None or (current_time - segment_start_time) >= SEGMENT_DURATION:
                # Закрываем предыдущий writer
                if writer is not None:
                    writer.release()
                    print(f'Сегмент завершен. Записано кадров: {frame_count}')

                # Создаем новый файл
                timestamp = datetime_now_str()
                filename = OUTPUT_DIR / f'{timestamp}.mp4'

                base_writer, _, avi_filename = get_video_writer(cap, str(filename))

                if not base_writer.is_opened():
                    print(f'ОШИБКА: Не удалось создать VideoWriter для {filename}')
                    time.sleep(1)
                    continue

                writer = FlushableVideoWriter(base_writer, avi_filename)
                segment_start_time = current_time
                frame_count = 0
                print(f'Начата запись нового сегмента: {avi_filename}')

            writer.write(frame)
            frame_count += 1

            time.sleep(0.001)

    except KeyboardInterrupt:
        print('\nПолучен сигнал остановки (Ctrl+C)')
    except Exception as e:
        print(f'Непредвиденная ошибка: {e}')
    finally:
        if writer is not None:
            writer.release()
            print('VideoWriter закрыт')
        if cap is not None:
            cap.release()
            print('VideoCapture закрыт')
        print('Запись завершена')


if __name__ == '__main__':
    record_stream()
