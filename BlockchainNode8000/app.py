from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from block_class import Block, Transaction
from blockchain import Blockchain
import json
import time
from ecdsa import SigningKey, VerifyingKey, NIST384p, BadSignatureError
import requests
import psycopg
from typing import Optional
from datetime import date
from threading import Lock
import os

app = FastAPI()

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class User(BaseModel):
    matricula: int
    cv: str
    nome: Optional[str] = None
    curso: Optional[str] = None
    unidade: Optional[str] = None
    rg: Optional[str] = None
    data_expedicao: Optional[date] = None
    data_nascimento: Optional[date] = None

class RechargeRequest(BaseModel):
    student_id: int
    amount: float
    signature: str
    public_key: str

class PaymentRequest(BaseModel):
    student_id: int
    codigo_seguranca: str
    amount: float
    signature: str
    public_key: str

class SignData(BaseModel):
    tx_data: str
    private_key: str


class RUToken:
    def __init__(self, blockchain=None):
        self.blockchain = Blockchain(difficulty=2,db_connection_string="postgresql://postgres:123456@db:5432/alunos")
        self.balances_cache = self._calculate_balances()
        self.lock = Lock()

    def _calculate_balances(self) -> dict:
        """Calcula os saldos a partir do blockchain"""
        balances = {}
        for block in self.blockchain.blocks:
            for tx in block.transactions:
                if tx.sender not in balances:
                    balances[tx.sender] = 0.0
                if tx.recipient not in balances:
                    balances[tx.recipient] = 0.0
                balances[tx.sender] -= tx.amount
                balances[tx.recipient] += tx.amount
        print("Balancas: ", balances)
        return balances

    def _mine_transaction(self, tx: Transaction):
        """Mina uma transação imediatamente e atualiza o cache"""
        with self.lock:
            # Adiciona a transação e minera um novo bloco
            self.blockchain.add_transaction(tx)
            self.blockchain.mine_block()  # Minera um bloco com apenas esta transação

            # Atualiza o cache de saldos
            self._update_balance_cache(tx)

            # Persiste a blockchain no arquivo
            self.blockchain.save()

    def _sign_transaction_data(self, private_key: str, tx_data: dict) -> str:
        """Assina os dados da transação de forma consistente"""
        try:
            # Garante formato JSON consistente (keys ordenadas, sem espaços)
            tx_json = json.dumps(tx_data, sort_keys=True, separators=(',', ':'))
            sk = SigningKey.from_pem(private_key.encode())
            signature = sk.sign(tx_json.encode())
            return signature.hex()
        except Exception as e:
            raise ValueError(f"Falha ao assinar transação: {str(e)}")


    def _process_transaction(self, tx: Transaction):
        """Processa uma transação: adiciona, minera e salva"""
        with self.lock:
            try:
                # 1. Adiciona à pool de transações
                self.blockchain.add_transaction(tx)

                # 2. Minera um bloco com todas as transações pendentes
                self.blockchain.mine_block()

                # 3. Salva no arquivo imediatamente
                self.blockchain.save()

                # 4. Atualiza os saldos
                self._update_balance_cache(tx)

            except Exception as e:
                raise ValueError(f"Erro ao processar transação: {str(e)}")

    def recharge(self, student_id: int, amount: float, signature: str, public_key: str):
        """Recarrega na blockchain com mineração imediata"""
        try:
            # Cria a transação
            tx = Transaction("RU", str(student_id), amount, signature, public_key)

            # Processa a transação (mineração + salvamento)
            self._process_transaction(tx)

            return tx

        except Exception as e:
            raise ValueError(f"Falha na recarga: {str(e)}")

    def make_payment(self, student_id: int, codigo_seguranca: str, amount: float, signature: str, public_key: str):
        """Pagamento na blockchain com mineração imediata"""
        try:
            # Busca chaves no banco de dados
            with psycopg.connect("postgresql://postgres:123456@db:5432/alunos") as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT cv FROM alunos WHERE id = %s",
                        (student_id,)
                    )
                    result = cur.fetchone()
                    if not result:
                        raise ValueError(f"Aluno {student_id} não encontrado")

                    cv = result[0]

            # Verifica saldo
            if(cv != codigo_seguranca):
                raise ValueError("Código de segurança invalido")
            if self.balances_cache.get(str(student_id), 0) < amount:
                raise ValueError("Saldo insuficiente")

            # Cria a transação
            tx = Transaction(str(student_id), "RU", amount, signature, public_key)

            # Processa a transação (mineração + salvamento)
            self._process_transaction(tx)

            return tx

        except Exception as e:
            raise ValueError(f"Falha no pagamento: {str(e)}")

    def _update_balance_cache(self, tx: Transaction):
        """Atualiza o cache de saldos"""
        if tx.sender not in self.balances_cache:
            self.balances_cache[tx.sender] = 0.0
        if tx.recipient not in self.balances_cache:
            self.balances_cache[tx.recipient] = 0.0
        self.balances_cache[tx.sender] -= tx.amount
        self.balances_cache[tx.recipient] += tx.amount

    def get_balance(self, student_id: int) -> float:
        """Retorna o saldo do aluno"""
        return self.balances_cache.get(str(student_id), 0.0)

def format_timestamp(timestamp):
    """Converte timestamp Unix (float) para formato dd/mm/aaaa hh:mm"""
    try:
        # Converte para datetime (considerando o timestamp em segundos)
        dt = date.fromtimestamp(timestamp)
        print(dt)

        # Formata para o padrão brasileiro
        return dt.strftime("%d/%m/%Y")

    except Exception as e:
        print(f"Erro ao formatar timestamp {timestamp}: {str(e)}")
        return "Data inválida"

# Inicializa o sistema
ru_token = RUToken()

@app.post("/createUser")
def create_user(user: User):
    try:
        conn = psycopg.connect("postgresql://postgres:123456@db:5432/alunos")
        cur = conn.cursor()
        sk = SigningKey.generate(curve=NIST384p)
        vk = sk.verifying_key
        cur.execute("""
            INSERT INTO alunos(
                id, cv, nome, curso, unidade, rg, data_expedicao, data_nascimento
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s )
        """, (
            user.matricula,
            user.cv,
            user.nome,
            user.curso,
            user.unidade,
            user.rg,
            user.data_expedicao,
            user.data_nascimento,
        ))
        conn.commit()
        cur.close()
        conn.close()

        # Atualiza o cache de chaves públicas
        ru_token.public_keys[str(user.matricula)] = user.cv

        return {"message": "Usuário criado com sucesso!"}
    except Exception as e:
        return {"error": str(e)}

@app.delete("/student/{id}")
def delete_aluno(id: int):
    try:
        with psycopg.connect("postgresql://postgres:123456@db:5432/alunos") as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM alunos WHERE id = %s", (id,))
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Aluno não encontrado")

                # Remove a chave pública do cache
                if str(id) in ru_token.public_keys:
                    del ru_token.public_keys[str(id)]

        return {"message": "Aluno deletado com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/student")
def get_alunos():
    try:
        with psycopg.connect("postgresql://postgres:123456@db:5432/alunos") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM alunos")
                rows = cur.fetchall()
        return {"alunos": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/generate_keys")
def generate_keys():
    sk = SigningKey.generate(curve=NIST384p)
    vk = sk.verifying_key
    return {
        "private_key": sk.to_pem().decode(),
        "public_key": vk.to_pem().decode()
    }

@app.get("/student/{id}")
def get_aluno_by_id(id: int):
    try:
        with psycopg.connect("postgresql://postgres:123456@db:5432/alunos") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM alunos WHERE id = %s", (id,))
                aluno = cur.fetchone()
                if not aluno:
                    raise HTTPException(status_code=404, detail="Aluno não encontrado")
        return {
            "id": aluno[0],
            "cv": aluno[1],
            "nome": aluno[2],
            "curso": aluno[3],
            "unidade": aluno[4],
            "rg": aluno[5],
            "data_expedicao": aluno[6],
            "data_nascimento": aluno[7]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Novos Endpoints de Blockchain
@app.post("/recharge")
async def recharge(request: RechargeRequest):

    try:
        tx = ru_token.recharge(
            request.student_id,
            request.amount,
            request.signature,
            request.public_key

        )
        return {
            "status": "success",
            "message": "Recarga realizada",
            "transaction": tx.to_dict(),
            "new_balance": ru_token.get_balance(request.student_id)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/payment")
async def make_payment(request: PaymentRequest):
    try:
        tx = ru_token.make_payment(
            request.student_id,
            request.codigo_seguranca,
            request.amount,
            request.signature,
            request.public_key
        )
        return {
            "status": "success",
            "message": "Pagamento realizado",
            "transaction": tx.to_dict(),
            "new_balance": ru_token.get_balance(request.student_id)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/balance/{student_id}")
async def get_balance(student_id: int):
    return {
        "student_id": student_id,
        "balance": ru_token.get_balance(student_id)
    }

@app.get("/chain")
async def get_full_chain():
    return {
        "chain": [block.to_dict() for block in ru_token.blockchain.blocks],
        "length": len(ru_token.blockchain.blocks)
    }

@app.post("/sign")
def sign_data(data: SignData):
    sk = SigningKey.from_pem(data.private_key.encode())
    signature = sk.sign(data.tx_data.encode())
    return {"signature": signature.hex()}

@app.get("/transaction_history/{student_id}")
async def get_transaction_history(student_id: int):
    try:
        student_id_str = str(student_id)
        history = []

        for block in ru_token.blockchain.blocks:
            for tx in block.transactions:
                if tx.sender == student_id_str or tx.recipient == student_id_str:
                    transaction_type = "pagamento" if tx.sender == student_id_str else "recarga"

                    history.append({
                        "amount": tx.amount,
                        "timestamp": block.timestamp,  # <-- Não formata ainda
                        "type": transaction_type,
                    })

        # Ordena por timestamp numérico
        history.sort(key=lambda x: x["timestamp"], reverse=True)

        # Depois formata os timestamps
        for tx in history:
            tx["timestamp"] = format_timestamp(tx["timestamp"])

        return {
            "student_id": student_id,
            "transaction_count": len(history),
            "transactions": history
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))