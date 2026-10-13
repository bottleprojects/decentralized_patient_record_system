import os
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

RPC_URL = os.getenv("SEPOLIA_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

# In a real app, this ABI would be loaded from the compiled contract JSON
# This matches the PatientRecord.sol from Phase 1 requirements
CONTRACT_ABI = json.loads('''[
    {"inputs": [{"internalType": "string","name": "recordId","type": "string"},{"internalType": "string","name": "recordHash","type": "string"}],"name": "storeRecordHash","outputs": [],"stateMutability": "nonpayable","type": "function"},
    {"inputs": [{"internalType": "string","name": "recordId","type": "string"}],"name": "getRecordHash","outputs": [{"internalType": "string","name": "","type": "string"}],"stateMutability": "view","type": "function"}
]''')

class BlockchainService:
    def __init__(self):
        if not RPC_URL or not PRIVATE_KEY or not CONTRACT_ADDRESS:
            # We don't raise error on init to allow backend to start without it for MVP testing,
            # but transactions will fail.
            self.w3 = None
            print("WARNING: Blockchain credentials not fully configured.")
            return

        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        # Sepolia is POA, need this middleware
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        if not self.w3.is_connected():
            print("WARNING: Failed to connect to Sepolia RPC.")
            
        self.account = self.w3.eth.account.from_key(PRIVATE_KEY)
        self.contract = self.w3.eth.contract(address=CONTRACT_ADDRESS, abi=CONTRACT_ABI)

    def store_record_hash(self, record_id: str, record_hash: str) -> str:
        """
        Stores the SHA-256 hash of a medical record on the Sepolia blockchain.
        Returns the transaction hash.
        """
        if not self.w3 or not self.w3.is_connected():
            raise Exception("Blockchain not connected (Check RPC_URL)")

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        
        # Build transaction
        tx = self.contract.functions.storeRecordHash(
            record_id, 
            record_hash
        ).build_transaction({
            'from': self.account.address,
            'nonce': nonce,
            # Let Web3 estimate gas and gas price
        })

        # Sign transaction
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        
        # Send transaction
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        return self.w3.to_hex(tx_hash)

blockchain_service = BlockchainService()
