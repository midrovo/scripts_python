
import imaplib
import email
import json
import os
import re
from email.header import decode_header
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('PASSWORD')
SENDER = os.getenv('SENDER')

# Archivo para guardar los IDs procesados
PROCESSED_IDS_FILE = 'processed_emails.json'

# Servidor
IMAP_SERVER = 'imap.gmail.com'

def load_processed_ids():
    if os.path.exists(PROCESSED_IDS_FILE):
        with open(PROCESSED_IDS_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_processed_ids(processed_ids):
    with open(PROCESSED_IDS_FILE, 'w') as f:
        json.dump(list(processed_ids), f)

def check_emails():
    # Cargar IDs ya procesados
    processed_ids = load_processed_ids()
    new_emails = False
    
    try:
        with imaplib.IMAP4_SSL(IMAP_SERVER) as mail:
            mail.login(EMAIL, PASSWORD)
            mail.select('INBOX')
            
            # Buscar correos desde el remitente en los últimos X minutos
            since_date = (datetime.now() - timedelta(minutes=1440)).strftime("%d-%b-%Y")  # 24 horas
            result, data = mail.search(None, f'(FROM "{SENDER}" SINCE "{since_date}")')
            
            if result != 'OK':
                print("Error al buscar correos")
                return
            
            email_ids = [id.decode() for id in data[0].split()]  # Convertir bytes a str
            
            for email_id in email_ids:
                if email_id in processed_ids:
                    continue  # Saltar correos ya procesados
                
                result, data = mail.fetch(email_id, '(RFC822)')
                if result != 'OK':
                    continue
                
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Decodificar asunto
                subject = decode_header(msg['Subject'])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                # Procesar cuerpo del mensaje
                body = ""
                for part in msg.walk():
                    if part.get_content_type() == 'text/plain':
                        body = part.get_payload(decode=True).decode('utf-8', errors='replace')
                        break
                
                datajson = parse_message(body)
                if datajson.get('NumberStat'):
                    print(f'\nNuevo correo procesado - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
                    print(f'ID: {email_id}')
                    print(f'Asunto: {subject}')
                    print(f'Mensaje: {datajson.get('NumberStat')[0]}')
                    print('-----------------------------')
                
                # Marcar como procesado
                processed_ids.add(email_id)
                new_emails = True
            
            # Guardar los nuevos IDs procesados
            if new_emails:
                save_processed_ids(processed_ids)
                print("Estado de procesamiento guardado.")

    except Exception as e:
        print(f"Error: {e}")


def parse_message(text):
    text = text.strip()

    # Intentamos primero interpretar como JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass  # No es JSON, seguimos con el análisis como texto plano

    # Si no es JSON, lo interpretamos como texto plano tipo clave: valor
    parsed = {}
    for line in text.splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            parsed[key.strip()] = value.strip()
    return parsed


if __name__ == "__main__":
    check_emails()