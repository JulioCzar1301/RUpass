import hashlib
import json
from ecdsa import VerifyingKey, BadSignatureError


class Transaction:
    def __init__(self, sender, recipient, amount, signature=None, public_key=None):
        self.sender = sender
        self.recipient = recipient
        self.amount = amount
        self.signature = signature
        print(self.signature)
        self.public_key = public_key

    def to_dict(self):
        return {
            "sender": self.sender,
            "recipient": self.recipient,
            "amount": self.amount,
            "signature": self.signature,
            "public_key": self.public_key
        }

    def is_valid(self):
        if not self.signature or not self.public_key:
            return False
        try:
            tx_data_dict = {
                "amount": f"{self.amount:.1f}",
                "recipient": self.recipient,
                "sender": self.sender
            }
            tx_data_json = json.dumps(tx_data_dict, sort_keys=True, separators=(',', ':'))
            vk = VerifyingKey.from_pem(self.public_key.encode())
            vk.verify(bytes.fromhex(self.signature), tx_data_json.encode())
            return True
        except (BadSignatureError, Exception):
            return False


class Block:
    def __init__(self, index, timestamp, previous_hash, transactions, nonce=0, hash=None):
        self.index = index
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.transactions = transactions  # Lista de Transaction
        self.nonce = nonce
        self.hash = hash or self.calculate_hash()

    def calculate_hash(self):
        data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "nonce": self.nonce
        }
        block_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def proof_of_work(self, difficulty):
        prefix = '0' * difficulty
        while not self.calculate_hash().startswith(prefix):
            self.nonce += 1
        self.hash = self.calculate_hash()

    def to_dict(self):
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "nonce": self.nonce,
            "hash": self.hash
        }
