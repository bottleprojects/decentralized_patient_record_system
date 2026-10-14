import os
import json
from datetime import datetime
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from pathlib import Path

RPC_URL = os.getenv("SEPOLIA_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
SIMULATE_BLOCKCHAIN = os.getenv("SIMULATE_BLOCKCHAIN", "false").lower() == "true"

if ENVIRONMENT == "production" and SIMULATE_BLOCKCHAIN:
    raise RuntimeError("FATAL [Blockchain]: SIMULATE_BLOCKCHAIN cannot be enabled in the production environment.")

# Load ABI from file located inside backend folder
ABI_FILE = Path(__file__).resolve().parent.parent / "contracts" / "PatientRecord.json"
if ABI_FILE.exists():
    with open(ABI_FILE, "r", encoding="utf-8") as _f:
        CONTRACT_ABI = json.load(_f)
else:
    raise RuntimeError(f"FATAL [Blockchain]: Contract ABI file not found at {ABI_FILE}")


class BlockchainService:
    def __init__(self):
        self.simulate_blockchain = SIMULATE_BLOCKCHAIN
        self.max_daily_tx = int(os.getenv("MAX_DAILY_TRANSACTIONS", "50"))

        is_placeholder = any(p in str(x).lower() for x in [RPC_URL, PRIVATE_KEY, CONTRACT_ADDRESS] for p in ["your", "placeholder"])
        if not RPC_URL or not PRIVATE_KEY or not CONTRACT_ADDRESS or is_placeholder or not Web3.is_address(CONTRACT_ADDRESS):
            self.w3 = None
            self.contract = None
            if ENVIRONMENT == "production":
                raise RuntimeError("FATAL [Blockchain]: Valid SEPOLIA_RPC_URL, PRIVATE_KEY, and CONTRACT_ADDRESS are required in production.")
            print("WARNING: Blockchain credentials not fully configured or using placeholders.")
            return

        self.w3 = Web3(Web3.HTTPProvider(RPC_URL))
        # Sepolia is POA, inject middleware
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        if not self.w3.is_connected():
            if ENVIRONMENT == "production":
                raise RuntimeError("FATAL [Blockchain]: Failed to connect to Sepolia RPC endpoint in production.")
            print("WARNING: Failed to connect to Sepolia RPC.")
            self.contract = None
            return

        self.account = self.w3.eth.account.from_key(PRIVATE_KEY)
        self.contract = self.w3.eth.contract(address=self.w3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)

    def _check_and_increment_daily_tx(self) -> int:
        """Enforces and records daily transaction count in the database to survive restarts."""
        from ..database import SessionLocal, engine, Base
        from ..models import BlockchainTransactionCounter

        Base.metadata.create_all(bind=engine)
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        with SessionLocal() as db:
            counter = db.query(BlockchainTransactionCounter).filter(BlockchainTransactionCounter.date_str == today_str).first()
            if not counter:
                counter = BlockchainTransactionCounter(date_str=today_str, tx_count=0)
                db.add(counter)
                db.commit()
                db.refresh(counter)

            if counter.tx_count >= self.max_daily_tx:
                raise RuntimeError(
                    f"Daily blockchain anchoring limit ({self.max_daily_tx} transactions) reached for {today_str}. "
                    "Transactions paused to protect the Sepolia faucet wallet from gas drainage."
                )

            counter.tx_count += 1
            counter.updated_at = datetime.utcnow()
            db.commit()
            return counter.tx_count

    def get_daily_tx_count(self) -> int:
        """Returns the number of blockchain transactions anchored today."""
        from ..database import SessionLocal, engine, Base
        from ..models import BlockchainTransactionCounter

        Base.metadata.create_all(bind=engine)
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        with SessionLocal() as db:
            counter = db.query(BlockchainTransactionCounter).filter(BlockchainTransactionCounter.date_str == today_str).first()
            return counter.tx_count if counter else 0

    def _send_tx(self, fn_call) -> str:
        """Helper: check limits and balance, build, sign, and send a transaction. Returns tx hash hex."""
        # 1. Enforce database-backed daily transaction limit
        self._check_and_increment_daily_tx()

        # 2. Check wallet balance before broadcasting
        balance_wei = self.w3.eth.get_balance(self.account.address)
        min_required_wei = self.w3.to_wei(0.0002, "ether")
        if balance_wei < min_required_wei:
            balance_eth = self.w3.from_wei(balance_wei, "ether")
            raise RuntimeError(
                f"Wallet balance too low: {balance_eth:.6f} Sepolia ETH remaining. "
                "At least 0.0002 ETH is required for transaction gas fees."
            )

        # 3. Build, sign, and broadcast transaction
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
        if not self.w3 or not self.w3.is_connected() or not self.contract:
            if self.simulate_blockchain:
                print("NOTICE: Anchoring simulated via SIMULATE_BLOCKCHAIN=true.")
                return f"0xsimulated_tx_{record_id[:8]}"
            raise RuntimeError(
                "Blockchain service is not connected to Sepolia. Transaction cannot be anchored. "
                "Set SIMULATE_BLOCKCHAIN=true in development to mock anchoring."
            )
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
        if not self.w3 or not self.w3.is_connected() or not self.contract:
            if self.simulate_blockchain:
                print("NOTICE: Anchoring simulated via SIMULATE_BLOCKCHAIN=true.")
                return f"0xsimulated_tx_{record_id[:8]}"
            raise RuntimeError(
                "Blockchain service is not connected to Sepolia. Transaction cannot be anchored. "
                "Set SIMULATE_BLOCKCHAIN=true in development to mock anchoring."
            )
        return self._send_tx(
            self.contract.functions.storeIPFSRecord(
                record_id, cid, sha256_hash, file_name, file_type, file_size
            )
        )

    def get_ipfs_record(self, record_id: str) -> dict:
        """
        Reads the anchored IPFS metadata directly from the Sepolia contract.
        Returns dict with cid, sha256_hash, file_name, file_type, file_size, timestamp.
        """
        if not self.w3 or not self.w3.is_connected() or not self.contract:
            if self.simulate_blockchain:
                return {
                    "cid": "QmSimulatedCID",
                    "sha256_hash": "simulated_hash",
                    "file_name": "simulated.pdf",
                    "file_type": "PDF",
                    "file_size": 1024,
                    "timestamp": int(datetime.utcnow().timestamp()),
                }
            raise RuntimeError("Blockchain service is not connected to Sepolia to verify on-chain record.")

        data = self.contract.functions.getIPFSRecord(record_id).call()
        return {
            "cid": data[0],
            "sha256_hash": data[1],
            "file_name": data[2],
            "file_type": data[3],
            "file_size": data[4],
            "timestamp": data[5],
        }

    def get_record_hash(self, record_id: str) -> str:
        """
        Reads hash from public mapping recordHashes(recordId).
        """
        if not self.w3 or not self.w3.is_connected() or not self.contract:
            if self.simulate_blockchain:
                return "simulated_hash"
            raise RuntimeError("Blockchain service is not connected to Sepolia to verify on-chain record.")
        return self.contract.functions.recordHashes(record_id).call()


blockchain_service = BlockchainService()
