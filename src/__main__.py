import cv2
import os
import time
from datetime import datetime
from pathlib import Path

# Получаем параметры из переменных окружения
RTSP_URL = os.getenv('RTSP_URL')
SEGMENT_DURATION = int(os.getenv('SEGMENT_DURATION', '300'))  # По умолчанию 5 минут

# Папка для сохранения видео
OUTPUT_DIR = Path('data')
OUTPUT_DIR.mkdir(exist_ok=True)

# Параметры переподключения
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 5  # секунд


def get_video_writer(cap, filename):
    """Создает VideoWriter с параметрами из захваченного потока"""
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps == 0:
        fps = 25  # Значение по умолчанию
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Используем MP4V кодек для лучшей совместимости
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    writer = cv2.VideoWriter(filename, fourcc, fps, (width, height))
    return writer, fps


def connect_to_stream():
    """Подключается к RTSP потоку с повторными попытками"""
    for attempt in range(MAX_RECONNECT_ATTEMPTS):
        print(f"Попытка подключения к {RTSP_URL} (попытка {attempt + 1}/{MAX_RECONNECT_ATTEMPTS})")
        
        cap = cv2.VideoCapture(RTSP_URL)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # Минимальный буфер для уменьшения задержки
        
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print("Успешное подключение к потоку")
                return cap
            else:
                print("Не удалось прочитать кадр")
                cap.release()
        
        if attempt < MAX_RECONNECT_ATTEMPTS - 1:
            print(f"Ожидание {RECONNECT_DELAY} секунд перед следующей попыткой...")
            time.sleep(RECONNECT_DELAY)
    
    return None


def record_stream():
    """Основная функция записи потока"""
    if not RTSP_URL:
        print("ОШИБКА: RTSP_URL не задан в переменных окружения")
        return
    
    print(f"Запуск записи RTSP потока")
    print(f"URL: {RTSP_URL}")
    print(f"Длительность сегмента: {SEGMENT_DURATION} секунд")
    print(f"Папка для сохранения: {OUTPUT_DIR}")
    
    cap = None
    writer = None
    segment_start_time = None
    frame_count = 0
    
    try:
        while True:
            # Подключение к потоку
            if cap is None or not cap.isOpened():
                cap = connect_to_stream()
                if cap is None:
                    print("Не удалось подключиться к потоку. Завершение.")
                    break
                
                # Закрываем предыдущий writer если был открыт
                if writer is not None:
                    writer.release()
                    writer = None
                
                segment_start_time = None
            
            # Чтение кадра
            ret, frame = cap.read()
            
            if not ret:
                print("Потеря соединения или ошибка чтения кадра")
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
                    print(f"Сегмент завершен. Записано кадров: {frame_count}")
                
                # Создаем новый файл
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = OUTPUT_DIR / f"segment_{timestamp}.mp4"
                
                writer, fps = get_video_writer(cap, str(filename))
                
                if not writer.isOpened():
                    print(f"ОШИБКА: Не удалось создать VideoWriter для {filename}")
                    time.sleep(1)
                    continue
                
                segment_start_time = current_time
                frame_count = 0
                print(f"Начата запись нового сегмента: {filename}")
            
            # Запись кадра
            writer.write(frame)
            frame_count += 1
            
            # Небольшая задержка для снижения нагрузки на CPU
            time.sleep(0.001)
    
    except KeyboardInterrupt:
        print("\nПолучен сигнал остановки (Ctrl+C)")
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}")
    finally:
        # Освобождение ресурсов
        if writer is not None:
            writer.release()
            print("VideoWriter закрыт")
        if cap is not None:
            cap.release()
            print("VideoCapture закрыт")
        print("Запись завершена")


if __name__ == "__main__":
    record_stream()