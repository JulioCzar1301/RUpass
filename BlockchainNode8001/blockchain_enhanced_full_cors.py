from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from block_class import Block, Transaction
from blockchain import Blockchain
import json
import time
from ecdsa import SigningKey, VerifyingKey, NIST384p, BadSignatureError
import requests

app = FastAPI()

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ou restrinja para ["http://localhost:8000"] se quiser
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

blockchain = Blockchain(difficulty=2)
peers = set()

@app.get("/generate_keys")
def generate_keys():
    sk = SigningKey.generate(curve=NIST384p)
    vk = sk.verifying_key
    return {
        "private_key": sk.to_pem().decode(),
        "public_key": vk.to_pem().decode()
    }

class SignData(BaseModel):
    tx_data: str
    private_key: str

@app.post("/sign")
def sign_data(data: SignData):
    sk = SigningKey.from_pem(data.private_key.encode())
    signature = sk.sign(data.tx_data.encode())
    return {"signature": signature.hex()}

class TransactionData(BaseModel):
    sender: str
    recipient: str
    amount: float
    signature: str
    public_key: str

@app.post("/transaction")
def add_transaction(tx: TransactionData):
    transaction = Transaction(**tx.dict())
    if not transaction.is_valid():
        return {"detail": "Transação inválida"}, 400
    blockchain.add_transaction(transaction)
    return {"message": "Transação adicionada"}

@app.post("/mine")
def mine():
    if not blockchain.transaction_pool:
        return {"message": "Nenhuma transação para minerar"}
    block = blockchain.mine_block()
    return {"message": "Bloco minerado", "block": block.to_dict()}

@app.get("/chain")
def get_chain():
    return [block.to_dict() for block in blockchain.blocks]

@app.get("/check_chain")
def check_chain():
    if blockchain.is_chain_valid():
        return {"valid": True}
    return {"valid": False, "message": "Blockchain foi corrompida!"}

@app.get("/hack_block")
def hack_block():
    if len(blockchain.blocks) > 1:
        blockchain.blocks[1].transactions[0].amount = 9999
        blockchain.blocks[1].hash = blockchain.blocks[1].calculate_hash()
        return {"message": "Bloco adulterado com sucesso"}
    return {"message": "Não há bloco suficiente para adulterar."}

@app.get("/export")
def export_chain():
    return [block.to_dict() for block in blockchain.blocks]

@app.post("/import")
def import_chain(received_chain: list):
    new_chain = []
    for b in received_chain:
        transactions = [Transaction(**tx) for tx in b["transactions"]]
        new_block = Block(
            index=b["index"],
            timestamp=b["timestamp"],
            previous_hash=b["previous_hash"],
            transactions=transactions,
            nonce=b.get("nonce", 0)
        )
        new_chain.append(new_block)
    blockchain.blocks = new_chain
    blockchain.save()
    return {"message": "Blockchain importada com sucesso"}

@app.post("/peers/register")
def register_peer(peer_url: str):
    peers.add(peer_url)
    return {"peers": list(peers)}

@app.get("/peers")
def list_peers():
    return {"peers": list(peers)}

@app.get("/peers/sync")
def sync_with_peers():
    global blockchain
    longest_chain = blockchain.blocks
    for peer in peers:
        try:
            response = requests.get(f"{peer}/export")
            peer_chain = response.json()
            if len(peer_chain) > len(longest_chain):
                longest_chain = peer_chain
        except Exception:
            continue
    if len(longest_chain) > len(blockchain.blocks):
        new_chain = []
        for b in longest_chain:
            transactions = [Transaction(**tx) for tx in b["transactions"]]
            new_block = Block(
                index=b["index"],
                timestamp=b["timestamp"],
                previous_hash=b["previous_hash"],
                transactions=transactions,
                nonce=b["nonce"]
            )
            new_chain.append(new_block)
        blockchain.blocks = new_chain
        blockchain.save()
        return {"message": "Blockchain sincronizada com sucesso!"}
    return {"message": "Nenhuma cadeia mais longa encontrada."}