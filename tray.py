from logging import root
import tkinter as tk
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import threading

# Глобальна змінна для головного вікна
root = None

def set_root_window(window):
    global root
    root = window

def hide_window():
    global root
    if root is not None:
        root.withdraw()  # Приховує головне вікно

def create_image():
    """Створення зображення для іконки в треї."""
    image = Image.new('RGB', (64, 64), color=(0, 128, 255))  # блакитний фон іконки
    d = ImageDraw.Draw(image)
    d.rectangle((10, 10, 54, 54), fill=(255, 255, 0))  # жовтий квадрат
    return image

def on_exit(icon, item):
    """Вихід з програми через меню трея."""
    icon.stop()
    # Додано виведення з програми
    if 'root' in globals():
        root.quit()

def restore_window(icon, item):
    """Відновлення вікна з трея."""
    if 'root' in globals():
        root.deiconify()  # Показує головне вікно
    icon.stop()  # Зупиняє іконку в треї

def setup_tray():
    """Налаштування іконки для трея."""
    icon = Icon("MyApp", create_image(), menu=Menu(
        MenuItem("Відновити", restore_window),  # Додаємо опцію для відновлення
        MenuItem("Вийти", on_exit)
    ))
    icon.run()

def hide_window():
    """Сховати вікно і запустити трей у фоновому потоці."""
    root.withdraw()  # Приховує головне вікно
    threading.Thread(target=setup_tray).start()  # Запускає трей у фоновому потоці
