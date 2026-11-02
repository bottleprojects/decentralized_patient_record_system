// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title PatientRecord
 * @notice Immutable cryptographic anchor and event log for medical record hashes,
 *         hardware sensor acquisition manifests, and consent audit trails.
 * @dev PERMISSION & ACCESS CONTROL NOTICE:
 * Patient and doctor permissions, clinical authorization, and data encryption keys
 * are strictly ENFORCED by the application backend and relational database layer.
 * This smart contract serves as an immutable, tamper-evident public notary:
 * 1. Restricts metadata write operations to authorized backend notary accounts.
 * 2. Enforces record immutability (prevents malicious post-hoc overwrite of existing record hashes).
 * 3. Binds both decentralized content identifiers (IPFS CID + SHA-256) and hardware provenance (H_acq).
 * 4. Logs immutable, transparent audit events for record anchoring and consent updates.
 */
contract PatientRecord is Ownable, Pausable {
    // Custom errors for gas efficiency
    error UnauthorizedCaller(address caller);
    error RecordAlreadyExists(string recordId);
    error EmptyRecordIdentifier();
    error EmptyContentIdentifier();
    error EmptyDigest();
    error RecordNotFound(string recordId);
    error InvalidAddress();

    // Authorized writer whitelist (backend notary addresses)
    mapping(address => bool) public authorizedWriters;

    // Existing: Record hash storage for legacy integrity verification
    mapping(string => string) public recordHashes;

    // Enhanced IPFS & Provenance Record Structure
    struct IPFSRecord {
        string cid;             // IPFS CID (e.g. "Qm..." or "bafy...")
        string sha256Hash;      // SHA-256 of the original (pre-encrypt) file
        string acquisitionHash; // SHA-256 of hardware sensor acquisition manifest (H_acq)
        string fileName;        // Non-identifying label (e.g. "encrypted-record")
        string fileType;        // MIME category tag (e.g. "Vitals Telemetry")
        uint256 fileSize;       // File size in bytes
        uint256 timestamp;      // Unix timestamp of on-chain commit
        uint256 version;        // Record schema version
    }
    mapping(string => IPFSRecord) public ipfsRecords;

    // Audit events
    event ConsentGranted(address indexed patient, address indexed doctor, string recordId);
    event ConsentRevoked(address indexed patient, address indexed doctor, string recordId);
    event RecordHashed(address indexed submitter, string recordId, string ipfsOrStorageHash);
    event IPFSRecordStored(
        address indexed submitter,
        string recordId,
        string cid,
        string sha256Hash,
        uint256 timestamp
    );
    event IPFSRecordWithProvenanceStored(
        address indexed submitter,
        string recordId,
        string cid,
        string sha256Hash,
        string acquisitionHash,
        uint256 timestamp
    );
    event WriterAuthorizationChanged(address indexed writer, bool authorized);

    modifier onlyAuthorized() {
        if (msg.sender != owner() && !authorizedWriters[msg.sender]) {
            revert UnauthorizedCaller(msg.sender);
        }
        _;
    }

    constructor() Ownable(msg.sender) {
        authorizedWriters[msg.sender] = true;
    }

    function setWriterAuthorization(address writer, bool authorized) external onlyOwner {
        authorizedWriters[writer] = authorized;
        emit WriterAuthorizationChanged(writer, authorized);
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    // Store record hash for legacy integrity verification
    function storeRecordHash(string memory recordId, string memory hashValue) public whenNotPaused onlyAuthorized {
        if (bytes(recordId).length == 0) revert EmptyRecordIdentifier();
        if (bytes(hashValue).length == 0) revert EmptyDigest();
        if (bytes(recordHashes[recordId]).length > 0) revert RecordAlreadyExists(recordId);

        recordHashes[recordId] = hashValue;
        emit RecordHashed(msg.sender, recordId, hashValue);
    }

    // Store IPFS metadata on-chain (Backward-compatible signature)
    function storeIPFSRecord(
        string memory recordId,
        string memory cid,
        string memory sha256Hash,
        string memory fileName,
        string memory fileType,
        uint256 fileSize
    ) public whenNotPaused onlyAuthorized {
        storeIPFSRecordWithProvenance(recordId, cid, sha256Hash, "", fileName, fileType, fileSize);
    }

    // Enhanced: Store IPFS metadata with hardware acquisition provenance digest
    function storeIPFSRecordWithProvenance(
        string memory recordId,
        string memory cid,
        string memory sha256Hash,
        string memory acquisitionHash,
        string memory fileName,
        string memory fileType,
        uint256 fileSize
    ) public whenNotPaused onlyAuthorized {
        if (bytes(recordId).length == 0) revert EmptyRecordIdentifier();
        if (bytes(cid).length == 0) revert EmptyContentIdentifier();
        if (bytes(sha256Hash).length == 0) revert EmptyDigest();
        if (bytes(ipfsRecords[recordId].cid).length > 0) revert RecordAlreadyExists(recordId);

        ipfsRecords[recordId] = IPFSRecord({
            cid: cid,
            sha256Hash: sha256Hash,
            acquisitionHash: acquisitionHash,
            fileName: fileName,
            fileType: fileType,
            fileSize: fileSize,
            timestamp: block.timestamp,
            version: 1
        });

        emit IPFSRecordStored(msg.sender, recordId, cid, sha256Hash, block.timestamp);
        if (bytes(acquisitionHash).length > 0) {
            emit IPFSRecordWithProvenanceStored(msg.sender, recordId, cid, sha256Hash, acquisitionHash, block.timestamp);
        }
    }

    // Retrieve IPFS record metadata (Backward-compatible signature)
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

    // Retrieve full IPFS provenance record including acquisition digest
    function getIPFSProvenanceRecord(string memory recordId)
        external
        view
        returns (
            string memory cid,
            string memory sha256Hash,
            string memory acquisitionHash,
            string memory fileName,
            string memory fileType,
            uint256 fileSize,
            uint256 timestamp,
            uint256 version
        )
    {
        IPFSRecord memory r = ipfsRecords[recordId];
        if (bytes(r.cid).length == 0) revert RecordNotFound(recordId);
        return (
            r.cid,
            r.sha256Hash,
            r.acquisitionHash,
            r.fileName,
            r.fileType,
            r.fileSize,
            r.timestamp,
            r.version
        );
    }

    // Record consent audit events (Access permissions enforced by backend/database; caller must be authorized writer or contract owner)
    function grantConsent(address doctor, string memory recordId) public whenNotPaused onlyAuthorized {
        if (doctor == address(0)) revert InvalidAddress();
        emit ConsentGranted(msg.sender, doctor, recordId);
    }

    function revokeConsent(address doctor, string memory recordId) public whenNotPaused onlyAuthorized {
        if (doctor == address(0)) revert InvalidAddress();
        emit ConsentRevoked(msg.sender, doctor, recordId);
    }
}
