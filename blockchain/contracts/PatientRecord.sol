// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title PatientRecord
 * @notice Immutable cryptographic anchor and event log for medical record hashes and consent events.
 * @dev PERMISSION & ACCESS CONTROL NOTICE:
 * Access control, authentication, and permissions for patients and doctors are ENFORCED by
 * the application backend and relational database layer, NOT by this smart contract.
 * The smart contract functions (storeRecordHash, storeIPFSRecord, grantConsent, revokeConsent)
 * emit immutable audit events (ConsentGranted, ConsentRevoked, RecordHashed, IPFSRecordStored)
 * to provide cryptographic transparency and tamper-evident history on the Ethereum blockchain.
 * This contract does not restrict or enforce data read/write access permissions.
 */
contract PatientRecord {
    // Existing: Record hash storage for integrity verification
    mapping(string => string) public recordHashes;

    // Full IPFS record metadata (CID + SHA-256 hash + metadata)
    struct IPFSRecord {
        string cid;         // IPFS CID (e.g. "Qm...")
        string sha256Hash;  // SHA-256 of the original (pre-encrypt) file
        string fileName;    // Original file name
        string fileType;    // MIME type or document category
        uint256 fileSize;   // File size in bytes
        uint256 timestamp;  // Unix timestamp of upload
    }
    mapping(string => IPFSRecord) public ipfsRecords;

    // Consent audit events (Recorded for immutable logging only; access permissions are enforced by backend/DB)
    event ConsentGranted(address indexed patient, address indexed doctor, string recordId);
    event ConsentRevoked(address indexed patient, address indexed doctor, string recordId);
    event RecordHashed(address indexed patient, string recordId, string ipfsOrStorageHash);

    // Event for IPFS uploads
    event IPFSRecordStored(
        address indexed patient,
        string recordId,
        string cid,
        string sha256Hash,
        uint256 timestamp
    );

    // Store record hash for integrity verification
    function storeRecordHash(string memory recordId, string memory hashValue) public {
        recordHashes[recordId] = hashValue;
        emit RecordHashed(msg.sender, recordId, hashValue);
    }

    // Store IPFS metadata on-chain
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

    // Retrieve IPFS record metadata
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

    // Record consent audit events (Access permissions enforced by backend/database)
    function grantConsent(address doctor, string memory recordId) public {
        emit ConsentGranted(msg.sender, doctor, recordId);
    }

    function revokeConsent(address doctor, string memory recordId) public {
        emit ConsentRevoked(msg.sender, doctor, recordId);
    }
}
