import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
from tkcalendar import DateEntry
import tray
from utils import (
    log_event, schedule_block, get_scheduled_tasks,
    clean_completed_tasks, search_accounts, set_ldap_config,
    ConfigurationManager, create_directories, load_configurations_from_file,
    save_configurations_to_file
)
from tray import hide_window  # Імпорт функцій з tray.py

# Глобальні змінні
task_listbox = None  # Змінна для зберігання Listbox
config_manager = ConfigurationManager()  # Ініціалізація менеджера конфігурацій

# Функція для обробки закриття вікна
def on_closing():
    hide_window()  # Сховати вікно замість закриття

# Реєстрація обробника події закриття вікна
root = tk.Tk()
tray.set_root_window(root)  # Встановлюємо root у tray.py
root.protocol("WM_DELETE_WINDOW", on_closing)

# Додайте текстове поле для логів
log_text = tk.Text(root, state='disabled', width=50, height=10)  # Додаємо текстове поле для логів
log_text.pack(pady=5)

# Функція для оновлення списку імен акаунтів
def update_account_names(event=None):
    partial_name = account_name_entry.get()
    if partial_name:
        account_names = search_accounts(partial_name)
        account_name_entry['values'] = account_names

# Функція для збереження налаштувань LDAP
def save_ldap_settings():
    ldap_server = ldap_server_entry.get()
    username = username_entry.get()
    password = password_entry.get()
    base_dn = base_dn_entry.get()

    if not all([ldap_server, username, password, base_dn]):
        messagebox.showwarning("Warning", "Please fill in all LDAP fields.")
        return
    
    set_ldap_config(ldap_server, username, password, base_dn)
    messagebox.showinfo("Info", "LDAP settings saved successfully.")

# Функція для оновлення списку запланованих завдань
def update_scheduled_tasks():
    task_listbox.delete(0, tk.END)  # Очистити старі завдання
    for task in get_scheduled_tasks():
        if task['status'] == 'Active':
            formatted_time = task['scheduled_time'].strftime('%Y-%m-%d %H:%M')
            task_listbox.insert(tk.END, f"{task['account']} - {formatted_time}")  # Додаємо нові завдання

# Функція для періодичного оновлення списку завдань
def refresh_scheduled_tasks():
    clean_completed_tasks()
    update_scheduled_tasks()
    root.after(5000, refresh_scheduled_tasks)

# Функція для підтвердження і планування блокування
def confirm_and_schedule_block():
    account_name = account_name_entry.get()
    if not account_name:
        messagebox.showwarning("Warning", "Please enter an account name.")
        return
    if messagebox.askyesno("Confirm", f"Are you sure you want to schedule blocking for account '{account_name}'?"):
        schedule_block_account()

# Функція для планування блокування
def schedule_block_account():
    account_name = account_name_entry.get()
    scheduled_date = cal.get_date()
    scheduled_time_str = time_combobox.get()

    if account_name and scheduled_time_str:
        try:
            scheduled_time = datetime.strptime(f"{scheduled_date} {scheduled_time_str}", '%Y-%m-%d %H:%M')
            if schedule_block(account_name, scheduled_time, log_text):  # Передаємо log_text
                messagebox.showinfo("Scheduled", f"Account '{account_name}' will be blocked at {scheduled_time}.")
                update_scheduled_tasks()
            else:
                messagebox.showwarning("Warning", "Scheduled time must be in the future.")
        except ValueError:
            messagebox.showwarning("Warning", "Please enter a valid time format (HH:MM).")
    else:
        messagebox.showwarning("Warning", "Please enter an account name and a valid time.")


# Створення директорій
create_directories()

# Завантаження конфігурацій
load_configurations_from_file(config_manager)

# Встановлення іконки для вікна та панелі завдань
root.iconbitmap("app_icon.ico")
root.title("Schedule Block AD Account")

# Поля для введення налаштувань LDAP
tk.Label(root, text="LDAP Configuration").pack(pady=5)
ldap_frame = tk.Frame(root)
ldap_frame.pack(pady=5)

tk.Label(ldap_frame, text="LDAP Server:").grid(row=0, column=0, sticky="e")
ldap_server_entry = tk.Entry(ldap_frame, width=30)
ldap_server_entry.grid(row=0, column=1)

tk.Label(ldap_frame, text="Username:").grid(row=1, column=0, sticky="e")
username_entry = tk.Entry(ldap_frame, width=30)
username_entry.grid(row=1, column=1)

tk.Label(ldap_frame, text="Password:").grid(row=2, column=0, sticky="e")
password_entry = tk.Entry(ldap_frame, show="*", width=30)
password_entry.grid(row=2, column=1)

tk.Label(ldap_frame, text="Base DN:").grid(row=3, column=0, sticky="e")
base_dn_entry = tk.Entry(ldap_frame, width=30)
base_dn_entry.grid(row=3, column=1)

save_ldap_button = tk.Button(ldap_frame, text="Save LDAP Settings", command=save_ldap_settings)
save_ldap_button.grid(row=4, column=1, pady=5)

# Поле для введення імені облікового запису з автозаповненням
tk.Label(root, text="Enter account name:").pack(pady=5)
account_name_entry = ttk.Combobox(root, width=30)
account_name_entry.pack(pady=5)
account_name_entry.bind("<KeyRelease>", update_account_names)  # Автозаповнення при введенні символів

# Календар для вибору дати
tk.Label(root, text="Select date:").pack(pady=5)
cal = DateEntry(root, width=12, background='darkblue', foreground='white', borderwidth=2)
cal.pack(pady=5)

# Вибір часу
tk.Label(root, text="Select time:").pack(pady=5)
time_options = [f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in (0, 30)]
time_combobox = ttk.Combobox(root, values=time_options, width=30)
time_combobox.pack(pady=5)

# Кнопка для запланування блокування
block_button = tk.Button(root, text="Schedule Block Account", command=confirm_and_schedule_block)
block_button.pack(pady=20)

# Кнопка для згорнення програми в трей
minimize_button = tk.Button(root, text="Згорнути в трей", command=hide_window)
minimize_button.pack(pady=5)

# Список запланованих завдань
task_listbox = tk.Listbox(root, width=50)
task_listbox.pack(pady=5)

# Оновлення списку запланованих завдань
refresh_scheduled_tasks()

# Запуск головного циклу
root.mainloop()
