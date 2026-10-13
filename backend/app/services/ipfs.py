import os
import requests

PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_API_SECRET = os.getenv("PINATA_API_SECRET")
PINATA_GATEWAY = os.getenv("PINATA_GATEWAY", "https://gateway.pinata.cloud")

PINATA_PIN_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"


class IPFSService:
    def __init__(self):
        if not PINATA_API_KEY or not PINATA_API_SECRET:
            print("WARNING: Pinata credentials not configured. IPFS upload will fail.")

    def upload(self, file_bytes: bytes, filename: str) -> str:
        """
        Upload encrypted bytes to IPFS via Pinata.
        Returns the IPFS CID string (e.g. 'Qm...').
        """
        if not PINATA_API_KEY or not PINATA_API_SECRET:
            raise Exception("Pinata credentials (PINATA_API_KEY / PINATA_API_SECRET) are not set.")

        files = {
            "file": (filename, file_bytes, "application/octet-stream"),
        }
        headers = {
            "pinata_api_key": PINATA_API_KEY,
            "pinata_secret_api_key": PINATA_API_SECRET,
        }
        response = requests.post(PINATA_PIN_URL, files=files, headers=headers, timeout=60)
        if response.status_code != 200:
            raise Exception(f"Pinata upload failed [{response.status_code}]: {response.text}")

        return response.json()["IpfsHash"]

    def download(self, cid: str) -> bytes:
        """
        Fetch encrypted file bytes from IPFS via the configured Pinata gateway.
        """
        url = f"{PINATA_GATEWAY}/ipfs/{cid}"
        response = requests.get(url, timeout=60)
        if response.status_code != 200:
            raise Exception(f"IPFS fetch failed [{response.status_code}] for CID {cid}")
        return response.content


ipfs_service = IPFSService()
