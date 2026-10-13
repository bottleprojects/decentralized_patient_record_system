// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract PatientRecord {
    // Existing: Record hash storage for integrity verification
    mapping(string => string) public recordHashes;

    // New: Full IPFS record metadata (CID + SHA-256 hash + metadata)
    struct IPFSRecord {
        string cid;         // IPFS CID (e.g. "Qm...")
        string sha256Hash;  // SHA-256 of the original (pre-encrypt) file
        string fileName;    // Original file name
        string fileType;    // MIME type or document category
        uint256 fileSize;   // File size in bytes
        uint256 timestamp;  // Unix timestamp of upload
    }
    mapping(string => IPFSRecord) public ipfsRecords;

    // Consent events
    event ConsentGranted(address indexed patient, address indexed doctor, string recordId);
    event ConsentRevoked(address indexed patient, address indexed doctor, string recordId);
    event RecordHashed(address indexed patient, string recordId, string ipfsOrStorageHash);

    // New event for IPFS uploads
    event IPFSRecordStored(
        address indexed patient,
        string recordId,
        string cid,
        string sha256Hash,
        uint256 timestamp
    );

    // Existing function — unchanged
    function storeRecordHash(string memory recordId, string memory hashValue) public {
        recordHashes[recordId] = hashValue;
        emit RecordHashed(msg.sender, recordId, hashValue);
    }

    // New function: store IPFS metadata on-chain
    function storeIPFSRecord(
        string memory recordId,
        string memory cid,
        string memory sha256Hash,
        string memory fileName,
        string memory fileType,
        uint256 fileSize
    ) public {
        ipfsRecords[recordId] = IPFSRecord({
            cid: cid,
            sha256Hash: sha256Hash,
            fileName: fileName,
            fileType: fileType,
            fileSize: fileSize,
            timestamp: block.timestamp
        });
        emit IPFSRecordStored(msg.sender, recordId, cid, sha256Hash, block.timestamp);
    }

    // New function: retrieve IPFS record metadata
    function getIPFSRecord(string memory recordId)
        public
        view
        returns (
            string memory cid,
            string memory sha256Hash,
            string memory fileName,
            string memory fileType,
            uint256 fileSize,
            uint256 timestamp
        )
    {
        IPFSRecord memory r = ipfsRecords[recordId];
        return (r.cid, r.sha256Hash, r.fileName, r.fileType, r.fileSize, r.timestamp);
    }

    function grantConsent(address doctor, string memory recordId) public {
        emit ConsentGranted(msg.sender, doctor, recordId);
    }

    function revokeConsent(address doctor, string memory recordId) public {
        emit ConsentRevoked(msg.sender, doctor, recordId);
    }
}
