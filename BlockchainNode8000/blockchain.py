import time
import json
import os
from block_class import Block, Transaction
import psycopg

class Blockchain:
    def __init__(self, difficulty=2, db_connection_string="postgresql://postgres:123456@db:5432/alunos"):
        self.difficulty = difficulty
        self.blocks = []
        self.db_connection_string = db_connection_string
        self.transaction_pool = []

        # Carrega do banco de dados
        self._load_from_db()

        # Se não houver blocos, cria o genesis
        if not self.blocks:
            self.create_genesis_block()
        self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(0, time.time(), None, [])
        genesis.proof_of_work(self.difficulty)
        self.blocks.append(genesis)

    def latest_block(self):
        return self.blocks[-1]

    def add_transaction(self, transaction):
        self.transaction_pool.append(transaction)

    def mine_block(self):
        new_block = Block(
            index=self.latest_block().index + 1,
            timestamp=time.time(),
            previous_hash=self.latest_block().hash,
            transactions=self.transaction_pool.copy()
        )
        new_block.proof_of_work(self.difficulty)
        self.blocks.append(new_block)
        self.transaction_pool.clear()
        return new_block

    def is_chain_valid(self):
        if not self.blocks:
            return False
        for i in range(1, len(self.blocks)):
            current = self.blocks[i]
            prev = self.blocks[i - 1]
            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != prev.hash:
                return False
        return True

    def _load_from_db(self):
        """Carrega a blockchain do banco de dados"""
        try:
            with psycopg.connect(self.db_connection_string) as conn:
                with conn.cursor() as cur:
                    # Carrega blocos
                    cur.execute("SELECT block_data FROM blockchain ORDER BY id")
                    for (block_data,) in cur.fetchall():
                        block_dict = block_data
                        transactions = [
                            Transaction(
                                tx['sender'],
                                tx['recipient'],
                                tx['amount'],
                                tx.get('signature'),
                                tx.get('public_key')
                            ) for tx in block_dict['transactions']
                        ]

                        block = Block(
                            index=block_dict['index'],
                            timestamp=block_dict['timestamp'],
                            previous_hash=block_dict['previous_hash'],
                            transactions=transactions,
                            nonce=block_dict.get('nonce', 0),
                            hash=block_dict.get('hash')
                        )
                        self.blocks.append(block)

                    # Carrega transações pendentes
                    cur.execute("SELECT transaction_data FROM pending_transactions ORDER BY id")
                    for (tx_data,) in cur.fetchall():
                        tx_dict = json.loads(tx_data)
                        tx = Transaction(
                            tx_dict['sender'],
                            tx_dict['recipient'],
                            tx_dict['amount'],
                            tx_dict.get('signature'),
                            tx_dict.get('public_key')
                        )
                        self.transaction_pool.append(tx)

        except Exception as e:
            print(f"Erro ao carregar blockchain do banco de dados: {e}")
            raise

    def save(self):
        """Salva a blockchain no banco de dados"""
        with psycopg.connect(self.db_connection_string) as conn:
            with conn.cursor() as cur:
                try:
                    # Limpa as tabelas (simplificação - em produção usar abordagem incremental)
                    cur.execute("TRUNCATE TABLE blockchain, pending_transactions")

                    # Salva todos os blocos
                    for block in self.blocks:
                        block_dict = {
                            'index': block.index,
                            'timestamp': block.timestamp,
                            'previous_hash': block.previous_hash,
                            'nonce': block.nonce,
                            'hash': block.hash,
                            'transactions': [self._tx_to_dict(tx) for tx in block.transactions]
                        }
                        cur.execute(
                            "INSERT INTO blockchain (block_data) VALUES (%s)",
                            (json.dumps(block_dict),)
                        )

                    # Salva transações pendentes
                    for tx in self.transaction_pool:
                        tx_dict = self._tx_to_dict(tx)
                        cur.execute(
                            "INSERT INTO pending_transactions (transaction_data) VALUES (%s)",
                            (json.dumps(tx_dict),)
                        )

                    conn.commit()
                    print("Blockchain salva no PostgreSQL com sucesso")

                except Exception as e:
                    conn.rollback()
                    print(f"Erro ao salvar blockchain no banco de dados: {e}")
                    raise

    def _tx_to_dict(self, tx):
        """Converte transação para dicionário serializável"""
        return {
            'sender': tx.sender,
            'recipient': tx.recipient,
            'amount': float(tx.amount),
            'signature': tx.signature,
            'public_key': tx.public_key
        }