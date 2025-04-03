import json
import time
import hashlib
from typing import List
from ecdsa import SigningKey, VerifyingKey, NIST384p, BadSignatureError
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from threading import Lock

# ----------- MODELO DE TRANSAÇÃO -----------
class Transaction(BaseModel):
    sender: str
    recipient: str
    amount: float
    signature: str = ""
    public_key: str = ""

    def to_dict(self):
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "signature": self.signature,
            "public_key": self.public_key
        }

    def to_json(self):
        return json.dumps({
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": round(self.amount, 1)
        }, sort_keys=True)

    
    def is_valid(self):
        if not self.signature or not self.public_key:
            print("[ERRO] Assinatura ou chave ausente.")
            return False
        try:
            tx_data_dict = {
                "amount": f"{self.amount:.1f}",  # como string com .1f
                "recipient": self.recipient,
                "sender": self.sender
            }
            tx_data_json = json.dumps(tx_data_dict, sort_keys=True, separators=(',', ':'))
            print("[DEBUG] Verificando assinatura com JSON:", tx_data_json)

            vk = VerifyingKey.from_pem(self.public_key.encode())
            vk.verify(bytes.fromhex(self.signature), tx_data_json.encode())
            return True
        except BadSignatureError:
            print("[ERRO] Assinatura inválida!")
            return False
        except Exception as e:
            print("[ERRO EXCEÇÃO]", str(e))
            return False





# ----------- BLOCO -----------
class Block:
    def __init__(self, index, timestamp, previous_hash, transactions: List[Transaction], nonce=0):
        self.index = index
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.nonce = nonce
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        tx_str = json.dumps([tx.to_dict() for tx in self.transactions], sort_keys=True)
        block_string = f"{self.index}{self.timestamp}{self.previous_hash}{tx_str}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def proof_of_work(self, difficulty):
        target = '0' * difficulty
        while not self.hash.startswith(target):
            self.nonce += 1
            self.hash = self.calculate_hash()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "transactions": [tx.dict() for tx in self.transactions],
            "nonce": self.nonce,
            "hash": self.hash
        }

    @staticmethod
    def from_dict(data):
        transactions = [Transaction(**tx) for tx in data["transactions"]]
        return Block(data["index"], data["timestamp"], data["previous_hash"], transactions, data["nonce"])

# ----------- BLOCKCHAIN -----------
class Blockchain:
    def __init__(self, difficulty=2, file_path='blockchain.json'):
        self.difficulty = difficulty
        self.blocks = []
        self.pending_transactions = []
        self.file_path = Path(file_path)
        self.lock = Lock()
        self.load_or_create()

    def create_genesis_block(self):
        genesis_block = Block(0, time.time(), None, [])
        genesis_block.proof_of_work(self.difficulty)
        self.blocks.append(genesis_block)
        self.save()

    def latest_block(self):
        return self.blocks[-1]

    def add_transaction(self, transaction: Transaction):
        if transaction.is_valid():
            self.pending_transactions.append(transaction)
            return True
        return False

    def mine_block(self):
        with self.lock:
            if not self.pending_transactions:
                return False
            new_block = Block(len(self.blocks), time.time(), self.latest_block().hash, self.pending_transactions[:])
            new_block.proof_of_work(self.difficulty)
            self.blocks.append(new_block)
            self.pending_transactions = []
            self.save()
            return True

    def is_chain_valid(self):
        for i in range(1, len(self.blocks)):
            curr = self.blocks[i]
            prev = self.blocks[i - 1]
            if curr.hash != curr.calculate_hash():
                return False
            if curr.previous_hash != prev.hash:
                return False
        return True

    def save(self):
        with self.file_path.open('w') as f:
            json.dump([block.to_dict() for block in self.blocks], f, indent=2)

    def load_or_create(self):
        if self.file_path.exists():
            with self.file_path.open() as f:
                data = json.load(f)
                self.blocks = [Block.from_dict(b) for b in data]
        else:
            self.create_genesis_block()

    def tamper_block(self, index, fake_data):
        if 0 <= index < len(self.blocks):
            self.blocks[index].transactions = [Transaction(**fake_data)]
            self.blocks[index].hash = self.blocks[index].calculate_hash()
            self.save()

# ----------- FASTAPI + CORS -----------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

blockchain = Blockchain()

# ----------- ENDPOINTS -----------

@app.get("/chain")
def get_chain():
    return [block.to_dict() for block in blockchain.blocks]

@app.post("/transaction")
def add_transaction(tx: Transaction):
    if blockchain.add_transaction(tx):
        return {"message": "Transação adicionada ao pool"}
    raise HTTPException(status_code=400, detail="Transação inválida")

@app.post("/mine")
def mine():
    if blockchain.mine_block():
        return {"message": "Novo bloco minerado com sucesso"}
    raise HTTPException(status_code=400, detail="Nenhuma transação para minerar")

@app.post("/tamper/{index}")
def tamper_block(index: int, fake: Transaction):
    blockchain.tamper_block(index, fake.dict())
    return {"message": f"Bloco #{index} foi adulterado"}

@app.get("/validate")
def validate_chain():
    return {"valid": blockchain.is_chain_valid()}

@app.get("/generate_keys")
def api_generate_keys():
    private, public = generate_keys()
    return {"private_key": private, "public_key": public}

@app.post("/sign")
def api_sign(tx_data: str = Body(...), private_key: str = Body(...)):
    signature = sign_transaction(tx_data, private_key)
    return {"signature": signature}

@app.get("/hack_block")
def hack_block():
    if len(blockchain.blocks) > 1:
        # Acessa o primeiro bloco após o gênesis
        bloco = blockchain.blocks[1]
        if bloco.transactions:
            bloco.transactions[0].amount = 9999  # CORRUPÇÃO!
            bloco.hash = bloco.calculate_hash()
            return {"message": "Transação do bloco 1 adulterada com sucesso!"}
        return {"message": "Bloco 1 não tem transações para adulterar."}
    return {"message": "Blockchain muito curta para simular ataque."}



@app.get("/check_chain")
def check_chain():
    if blockchain.is_chain_valid():
        return {"valid": True, "message": "Blockchain íntegra"}
    return {"valid": False, "message": "Blockchain foi corrompida!"}

# ----------- FUNÇÕES DE CRIPTOGRAFIA -----------

def generate_keys():
    sk = SigningKey.generate(curve=NIST384p)
    vk = sk.verifying_key
    return sk.to_pem().decode(), vk.to_pem().decode()

def sign_transaction(tx_data: str, private_key_pem: str):
    sk = SigningKey.from_pem(private_key_pem)
    signature = sk.sign(tx_data.encode())
    return signature.hex()

def verify_signature(tx_data: str, signature_hex: str, public_key_pem: str):
    vk = VerifyingKey.from_pem(public_key_pem)
    return vk.verify(bytes.fromhex(signature_hex), tx_data.encode())
