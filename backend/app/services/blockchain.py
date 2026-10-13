import os
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

RPC_URL = os.getenv("SEPOLIA_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

# ABI includes both original and new IPFS functions
CONTRACT_ABI = json.loads('''[
    {"inputs": [{"internalType": "string","name": "recordId","type": "string"},{"internalType": "string","name": "recordHash","type": "string"}],"name": "storeRecordHash","outputs": [],"stateMutability": "nonpayable","type": "function"},
    {"inputs": [{"internalType": "string","name": "recordId","type": "string"}],"name": "getRecordHash","outputs": [{"internalType": "string","name": "","type": "string"}],"stateMutability": "view","type": "function"},
    {"inputs": [{"internalType": "string","name": "recordId","type": "string"},{"internalType": "string","name": "cid","type": "string"},{"internalType": "string","name": "sha256Hash","type": "string"},{"internalType": "string","name": "fileName","type": "string"},{"internalType": "string","name": "fileType","type": "string"},{"internalType": "uint256","name": "fileSize","type": "uint256"}],"name": "storeIPFSRecord","outputs": [],"stateMutability": "nonpayable","type": "function"},
    {"inputs": [{"internalType": "string","name": "recordId","type": "string"}],"name": "getIPFSRecord","outputs": [{"internalType": "string","name": "cid","type": "string"},{"internalType": "string","name": "sha256Hash","type": "string"},{"internalType": "string","name": "fileName","type": "string"},{"internalType": "string","name": "fileType","type": "string"},{"internalType": "uint256","name": "fileSize","type": "uint256"},{"internalType": "uint256","name": "timestamp","type": "uint256"}],"stateMutability": "view","type": "function"}
]''')


class BlockchainService:
    def __init__(self):
        is_placeholder = any(p in str(x).lower() for x in [RPC_URL, PRIVATE_KEY, CONTRACT_ADDRESS] for p in ["your", "placeholder"])
        if not RPC_URL or not PRIVATE_KEY or not CONTRACT_ADDRESS or is_placeholder or not Web3.is_address(CONTRACT_ADDRESS):
            # Allow backend to start without blockchain for testing / before deployment
            self.w3 = None
            self.contract = None
            print("WARNING: Blockchain credentials not fully configured or using placeholders.")
            return

        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        # Sepolia is POA, need this middleware
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not self.w3.is_connected():
            print("WARNING: Failed to connect to Sepolia RPC.")

        self.account = self.w3.eth.account.from_key(PRIVATE_KEY)
        self.contract = self.w3.eth.contract(address=self.w3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)

    def _send_tx(self, fn_call) -> str:
        """Helper: build, sign, and send a transaction. Returns tx hash hex."""
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        tx = fn_call.build_transaction({"from": self.account.address, "nonce": nonce})
        signed = self.w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return self.w3.to_hex(tx_hash)

    def store_record_hash(self, record_id: str, record_hash: str) -> str:
        """
        Stores the SHA-256 hash of a medical record on the Sepolia blockchain.
        Returns the transaction hash.
        """
        if not self.w3 or not self.w3.is_connected():
            print("WARNING: Blockchain not connected. Using simulated tx for test.")
            return f"0xsimulated_tx_{record_id[:8]}"
        return self._send_tx(
            self.contract.functions.storeRecordHash(record_id, record_hash)
        )

    def store_ipfs_record(
        self,
        record_id: str,
        cid: str,
        sha256_hash: str,
        file_name: str,
        file_type: str,
        file_size: int,
    ) -> str:
        """
        Stores IPFS metadata (CID, hash, name, type, size) on-chain.
        Returns the transaction hash.
        """
        if not self.w3 or not self.w3.is_connected():
            print("WARNING: Blockchain not connected. Using simulated tx for test.")
            return f"0xsimulated_tx_{record_id[:8]}"
        return self._send_tx(
            self.contract.functions.storeIPFSRecord(
                record_id, cid, sha256_hash, file_name, file_type, file_size
            )
        )


blockchain_service = BlockchainService()
