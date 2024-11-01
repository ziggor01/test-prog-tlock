# utils.py

import csv
from datetime import datetime
import subprocess
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
import threading
import tkinter as tk  # Додаємо цей імпорт для коректної роботи з tkinter

# Глобальні змінні для налаштувань LDAP
LDAP_SERVER = ''
USERNAME = ''
PASSWORD = ''
BASE_DN = ''

# Функція для налаштування LDAP-параметрів
def set_ldap_config(ldap_server, username, password, base_dn):
    global LDAP_SERVER, USERNAME, PASSWORD, BASE_DN
    LDAP_SERVER = ldap_server
    USERNAME = username
    PASSWORD = password
    BASE_DN = base_dn

# Функція для запуску синхронізації Entra ID
def sync_entra_id():
    try:
        subprocess.run(["powershell", "-Command", "Start-ADSyncSyncCycle -PolicyType Delta"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error synchronizing Entra ID: {str(e)}")

# Імена файлів для збереження логів
LOG_TXT_FILE = 'event_log.txt'
LOG_CSV_FILE = 'event_log.csv'

# Список для запланованих завдань
scheduled_tasks = []

# Функція для пошуку акаунтів за частковим ім'ям
def search_accounts(partial_name):
    account_names = []
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, USERNAME, PASSWORD, auto_bind=True)
        conn.search(BASE_DN, f'(&(objectClass=user)(sAMAccountName=*{partial_name}*))', attributes=['sAMAccountName'])
        
        account_names = [entry.sAMAccountName.value for entry in conn.entries]
    except Exception as ex:
        print(f"Error searching accounts: {str(ex)}")
    
    return account_names

# Функція для збереження логів у файли
def save_log_to_file(message):
    with open(LOG_TXT_FILE, 'a') as txt_file:
        txt_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    with open(LOG_CSV_FILE, 'a', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message])

# Функція для журналу подій
def log_event(log_text, message):
    log_text.config(state='normal')
    log_text.insert(tk.END, f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    log_text.config(state='disabled')
    save_log_to_file(message)

# Функція для блокування акаунту
def block_account(account_name, scheduled_time, log_text):
    try:
        server = Server(LDAP_SERVER, get_info=ALL)
        conn = Connection(server, USERNAME, PASSWORD, auto_bind=True)
        conn.search(BASE_DN, f'(&(objectClass=user)(sAMAccountName={account_name}))')
        
        if conn.entries:
            user_dn = conn.entries[0].entry_dn
            conn.modify(user_dn, {'userAccountControl': [(MODIFY_REPLACE, [0x0002])]} )
            log_event(log_text, f"Account '{account_name}' was blocked successfully.")
            # Оновлюємо статус завдання
            for task in scheduled_tasks:
                if task['account'] == account_name and task['scheduled_time'] == scheduled_time:
                    task['status'] = 'Completed'
                    break

            # Виконуємо синхронізацію Entra ID
            sync_entra_id()
            return "Account blocked successfully."
        else:
            log_event(log_text, f"Account '{account_name}' not found.")
            return "Account not found."
    except Exception as ex:
        log_event(log_text, f"Error blocking account '{account_name}': {str(ex)}")
        return f"Error blocking account '{account_name}': {str(ex)}"

# Функція для планування блокування акаунту
def schedule_block(account_name, scheduled_time, log_text):
    delay = (scheduled_time - datetime.now()).total_seconds()
    if delay > 0:
        task_info = {
            "account": account_name,
            "scheduled_time": scheduled_time,
            "status": "Active"
        }
        scheduled_tasks.append(task_info)
        threading.Timer(delay, block_account, args=(account_name, scheduled_time, log_text)).start()
        log_event(log_text, f"Scheduled blocking for '{account_name}' at {scheduled_time}.")
        return True
    else:
        log_event(log_text, "Scheduled time must be in the future.")
        return False

# Функція для перегляду запланованих завдань
def get_scheduled_tasks():
    return scheduled_tasks

# Функція для очищення завершених завдань
def clean_completed_tasks():
    global scheduled_tasks
    scheduled_tasks = [task for task in scheduled_tasks if task['status'] != 'Completed']
