from pymodbus.client import ModbusTcpClient
from firebase_admin import credentials, db
import firebase_admin
import time
import logging

# Configurar logging para depuração
logging.basicConfig(level=logging.INFO)

# ======================================
# CONFIGURAÇÕES PERSONALIZADAS (AJUSTE AQUI!)
# ======================================
FIREBASE_CREDENTIALS = "C:\Users\lusuq\OneDrive\Área de Trabalho\piui\VoltsFireBase\voltsteste-firebase-adminsdk-fbsvc-0790633160.json"  # Ex: "service-account.json"
FIREBASE_DB_URL = "https://console.firebase.google.com/project/voltsteste/database/voltsteste-default-rtdb/data/~2F"         # Ex: "https://sel-5030.firebaseio.com"
CLP_IP = "192.168.2.11.23"                                       # IP do CLP
MODBUS_PORT = 502                                              # Porta Modbus
UPDATE_INTERVAL = 0.5                                          # Intervalo de atualização (segundos)

# Lista dos 12 registros Modbus a serem lidos (ajuste conforme o manual do SEL 5030)
REGISTERS = [
    {"name": "Tensão_Fase_A_V", "address": 0, "scale": 0.1},   # Registro 0, escala x0.1
    {"name": "Corrente_Fase_A_A", "address": 1, "scale": 0.01},
    {"name": "Frequência_Hz", "address": 2, "scale": 0.01},
    {"name": "Potência_Ativa_kW", "address": 3, "scale": 1},
    {"name": "Potência_Reativa_kVAR", "address": 4, "scale": 1},
    {"name": "Fator_Potência", "address": 5, "scale": 0.001},
    {"name": "THD_Tensão_%", "address": 6, "scale": 0.1},
    {"name": "THD_Corrente_%", "address": 7, "scale": 0.1},
    {"name": "Temperatura_°C", "address": 8, "scale": 0.1},
    {"name": "Estado_Relé", "address": 9, "scale": 1},         # Valor binário (0 ou 1)
    {"name": "Alarme_Sobrecarga", "address": 10, "scale": 1},
    {"name": "Energia_Total_kWh", "address": 11, "scale": 10},
]
# ======================================

def main():
    # Inicializar Firebase
    try:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS)
        firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})
        logging.info("[Firebase] Conexão estabelecida com sucesso.")
    except Exception as e:
        logging.error(f"[Firebase] Erro de inicialização: {e}")
        return

    # Conectar ao CLP via Modbus
    client = ModbusTcpClient(CLP_IP, port=MODBUS_PORT)
    try:
        client.connect()
        logging.info(f"[Modbus] Conectado ao CLP em {CLP_IP}:{MODBUS_PORT}")
    except Exception as e:
        logging.error(f"[Modbus] Falha na conexão: {e}")
        return

    # Loop principal de leitura
    try:
        while True:
            data = {"timestamp": time.time()}
            
            # Ler cada registro da lista
            for reg in REGISTERS:
                try:
                    response = client.read_holding_registers(reg["address"], 1)
                    if not response.isError():
                        raw_value = response.registers[0]
                        scaled_value = raw_value * reg["scale"]
                        data[reg["name"]] = round(scaled_value, 3)  # Arredonda para 3 casas decimais
                    else:
                        logging.error(f"[Modbus] Erro no registro {reg['address']}: {response}")
                        data[reg["name"]] = None  # Valor nulo em caso de erro
                except Exception as e:
                    logging.error(f"[Modbus] Falha na leitura do registro {reg['address']}: {e}")
                    data[reg["name"]] = None

            # Enviar dados para o Firebase
            try:
                ref = db.reference('/clp_data')
                ref.push(data)
                logging.info("[Firebase] Dados enviados com sucesso.")
            except Exception as e:
                logging.error(f"[Firebase] Erro ao enviar dados: {e}")

            time.sleep(UPDATE_INTERVAL)

    except KeyboardInterrupt:
        logging.info("Script interrompido pelo usuário.")
    finally:
        client.close()
        logging.info("[Modbus] Conexão encerrada.")

if __name__ == "__main__":
    main()