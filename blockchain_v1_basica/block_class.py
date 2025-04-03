# block.py
# Classe que representa um bloco individual na blockchain
import hashlib
import time
import json
from biometric_data import BiometricData

class Block:
    def __init__(self, index, timestamp, previous_hash, data):
        """
        Inicializa um bloco com os atributos necessários
        :param index: Índice do bloco na blockchain
        :param timestamp: Timestamp de criação do bloco
        :param previous_hash: Hash do bloco anterior
        :param data: Dados armazenados no bloco (pode ser string ou BiometricData)
        """
        self.index = index
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.data = data
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self):
        """
        Calcula o hash do bloco utilizando SHA-256
        """
        # Converte os dados para string JSON se for BiometricData
        if isinstance(self.data, BiometricData):
            data_str = self.data.to_json()
        else:
            data_str = str(self.data)
            
        data_str = f"{self.index}{self.timestamp}{self.previous_hash}{data_str}{self.nonce}"
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def proof_of_work(self, difficulty):
        """
        Implementa o algoritmo de Proof-of-Work para validar o bloco
        :param difficulty: Nível de dificuldade definido para a blockchain
        """
        target = '0' * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def __str__(self):
        """
        Retorna a representação textual do bloco
        """
        data_str = self.data.to_json() if isinstance(self.data, BiometricData) else str(self.data)
        return f"Block #{self.index} [previousHash: {self.previous_hash}, timestamp: {time.ctime(self.timestamp)}, data: {data_str}, hash: {self.hash}]"
