# utils.py

import csv
from datetime import datetime
import subprocess
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
import threading
import tkinter as tk
import os
import json
import logging
from cryptography.fernet import Fernet  # type: ignore

# Налаштування журналювання
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)  # Створити папку logs, якщо вона не існує
logging.basicConfig(filename=os.path.join(log_dir, 'app.log'), level=logging.INFO)

class ConfigurationManager:
    def __init__(self):
        self.configurations = {}
        self.key = self.load_or_generate_key()  # Завантаження ключа або генерація нового

    def load_or_generate_key(self):
        """Завантаження ключа з файлу або генерація нового"""
        # Переконайтеся, що директорія існує
        os.makedirs('configurations', exist_ok=True)
        
        key_file = 'configurations/key.key'
        try:
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(key)
                return key
        except Exception as e:
            logging.error(f"Error loading or generating key: {e}")
            raise  # Пробросити виключення далі

    def add_configuration(self, name, config_data):
        """Додавання нової конфігурації"""
        encrypted_data = self.encrypt_data(json.dumps(config_data))
        self.configurations[name] = encrypted_data
        logging.info(f"Configuration '{name}' added.")

    def encrypt_data(self, data):
        """Шифрування даних"""
        f = Fernet(self.key)
        encrypted_data = f.encrypt(data.encode())
        return encrypted_data

    def get_configurations(self):
        """Отримання всіх конфігурацій"""
        return {name: self.decrypt_data(data) for name, data in self.configurations.items()}

    def decrypt_data(self, encrypted_data):
        """Дешифрування даних"""
        f = Fernet(self.key)
        decrypted_data = f.decrypt(encrypted_data).decode()
        return decrypted_data

    def delete_configuration(self, name):
        """Видалення конфігурації за назвою"""
        if name in self.configurations:
            del self.configurations[name]
            logging.info(f"Configuration '{name}' deleted.")

# Функція для створення папок
def create_directories():
    os.makedirs("configurations", exist_ok=True)
    os.makedirs("modules", exist_ok=True)
    os.makedirs("updates", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    logging.info("Directories created.")

# Збереження конфігурацій у файл
def save_configurations_to_file(manager, filename='configurations/configs.json'):
    try:
        with open(filename, 'w') as f:
            json.dump(manager.configurations, f)
        logging.info("Configurations saved to file.")
    except Exception as e:
        logging.error(f"Error saving configurations to file: {e}")

# Завантаження конфігурацій з файлу
def load_configurations_from_file(manager, filename='configurations/configs.json'):
    if os.path.exists(filename):
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                manager.configurations = {name: data[name] for name in data}
                
                # Завантажуємо налаштування LDAP, якщо вони є
                if "LDAPSettings" in manager.configurations:
                    ldap_settings = json.loads(manager.get_configurations()["LDAPSettings"])
                    ldap_server_entry.delete(0, tk.END)
                    ldap_server_entry.insert(0, ldap_settings["ldap_server"])
                    username_entry.delete(0, tk.END)
                    username_entry.insert(0, ldap_settings["username"])
                    password_entry.delete(0, tk.END)
                    password_entry.insert(0, ldap_settings["password"])
                    base_dn_entry.delete(0, tk.END)
                    base_dn_entry.insert(0, ldap_settings["base_dn"])
                
            logging.info("Configurations loaded from file.")
        except json.JSONDecodeError as e:
            logging.error(f"Error loading configurations from file: {e}")
            print("Error: The configuration file is not valid JSON or is empty.")
        except Exception as e:
            logging.error(f"Error opening configuration file: {e}")
            print("Error: Could not open the configuration file.")
    else:
        logging.warning("Configuration file does not exist.")
        print("Warning: Configuration file not found.")


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
    logging.info("LDAP configuration set.")

# Функція для запуску синхронізації Entra ID
def sync_entra_id():
    try:
        subprocess.run(["powershell", "-Command", "Start-ADSyncSyncCycle -PolicyType Delta"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error synchronizing Entra ID: {str(e)}")

# Імена файлів для збереження логів
LOG_TXT_FILE = 'logs/event_log.txt'
LOG_CSV_FILE = 'logs/event_log.csv'

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
        logging.error(f"Error searching accounts: {str(ex)}")
    
    return account_names

# Функція для збереження логів у файли
def save_log_to_file(message):
    try:
        with open(LOG_TXT_FILE, 'a') as txt_file:
            txt_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
        with open(LOG_CSV_FILE, 'a', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([datetime.now().strftime('%Y-%m-%d %H:%M:%S'), message])
    except Exception as e:
        logging.error(f"Error saving log to file: {e}")

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
    logging.info("Cleaned up completed tasks.")
