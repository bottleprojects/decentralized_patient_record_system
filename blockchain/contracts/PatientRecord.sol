// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract PatientRecord {
    // Record hash storage for integrity verification
    mapping(string => string) public recordHashes;

    // Consent events
    event ConsentGranted(address indexed patient, address indexed doctor, string recordId);
    event ConsentRevoked(address indexed patient, address indexed doctor, string recordId);
    event RecordHashed(address indexed patient, string recordId, string ipfsOrStorageHash);

    function storeRecordHash(string memory recordId, string memory hashValue) public {
        recordHashes[recordId] = hashValue;
        emit RecordHashed(msg.sender, recordId, hashValue);
    }

    function grantConsent(address doctor, string memory recordId) public {
        emit ConsentGranted(msg.sender, doctor, recordId);
    }

    function revokeConsent(address doctor, string memory recordId) public {
        emit ConsentRevoked(msg.sender, doctor, recordId);
    }
}
