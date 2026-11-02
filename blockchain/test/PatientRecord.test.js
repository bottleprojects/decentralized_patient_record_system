const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("PatientRecord Smart Contract Security & Provenance", function () {
  let PatientRecord, contract;
  let owner, writer, unauthorizedUser, doctor;

  beforeEach(async function () {
    [owner, writer, unauthorizedUser, doctor] = await ethers.getSigners();
    PatientRecord = await ethers.getContractFactory("PatientRecord");
    contract = await PatientRecord.deploy();
    await contract.waitForDeployment();
  });

  it("Should allow owner and authorized writers to store IPFS records", async function () {
    await contract.setWriterAuthorization(writer.address, true);

    const tx = await contract.connect(writer).storeIPFSRecord(
      "REC-001",
      "QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
      "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
      "encrypted-record",
      "Vitals Telemetry",
      2048
    );
    await tx.wait();

    const record = await contract.getIPFSRecord("REC-001");
    expect(record.cid).to.equal("QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG");
    expect(record.sha256Hash).to.equal("a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3");
    expect(record.fileName).to.equal("encrypted-record");
    expect(record.fileType).to.equal("Vitals Telemetry");
    expect(record.fileSize).to.equal(2048);
  });

  it("Should REJECT unauthorized accounts attempting to store records (Part 10.1)", async function () {
    await expect(
      contract.connect(unauthorizedUser).storeIPFSRecord(
        "REC-HACK",
        "QmHackedCID",
        "hacked_hash",
        "fake-record",
        "Fake",
        100
      )
    ).to.be.revertedWithCustomError(contract, "UnauthorizedCaller");
  });

  it("Should REJECT duplicate record IDs to prevent overwrite attacks (Part 10.2)", async function () {
    await contract.storeIPFSRecord(
      "REC-UNIQUE-01",
      "QmOriginalCID",
      "original_hash",
      "encrypted-record",
      "Vitals",
      1024
    );

    await expect(
      contract.storeIPFSRecord(
        "REC-UNIQUE-01",
        "QmTamperedCID",
        "tampered_hash",
        "encrypted-record",
        "Vitals",
        1024
      )
    ).to.be.revertedWithCustomError(contract, "RecordAlreadyExists");
  });

  it("Should REJECT empty record IDs or CIDs (Part 10.3)", async function () {
    await expect(
      contract.storeIPFSRecord("", "QmCID", "hash", "file", "type", 100)
    ).to.be.revertedWithCustomError(contract, "EmptyRecordIdentifier");

    await expect(
      contract.storeIPFSRecord("REC-EMPTY", "", "hash", "file", "type", 100)
    ).to.be.revertedWithCustomError(contract, "EmptyContentIdentifier");
  });

  it("Should store and retrieve full hardware provenance records (Part 7)", async function () {
    const acquisitionHash = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9";
    const fileHash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

    const tx = await contract.storeIPFSRecordWithProvenance(
      "REC-PROV-01",
      "QmProvenanceCID1234567890",
      fileHash,
      acquisitionHash,
      "encrypted-record",
      "ECG & SpO2",
      4096
    );
    await tx.wait();

    const prov = await contract.getIPFSProvenanceRecord("REC-PROV-01");
    expect(prov.cid).to.equal("QmProvenanceCID1234567890");
    expect(prov.sha256Hash).to.equal(fileHash);
    expect(prov.acquisitionHash).to.equal(acquisitionHash);
    expect(prov.version).to.equal(1);
  });

  it("Should respect emergency pause (Part 10.5)", async function () {
    await contract.pause();

    await expect(
      contract.storeIPFSRecord(
        "REC-PAUSED",
        "QmPausedCID",
        "hash",
        "file",
        "type",
        100
      )
    ).to.be.revertedWithCustomError(contract, "EnforcedPause");

    await contract.unpause();

    await expect(
      contract.storeIPFSRecord(
        "REC-PAUSED",
        "QmPausedCID",
        "hash",
        "file",
        "type",
        100
      )
    ).to.not.be.reverted;
  });

  it("Should emit immutable consent audit events (Part 10.4)", async function () {
    await expect(contract.connect(owner).grantConsent(doctor.address, "REC-CONSENT-01"))
      .to.emit(contract, "ConsentGranted")
      .withArgs(owner.address, doctor.address, "REC-CONSENT-01");

    await expect(contract.connect(owner).revokeConsent(doctor.address, "REC-CONSENT-01"))
      .to.emit(contract, "ConsentRevoked")
      .withArgs(owner.address, doctor.address, "REC-CONSENT-01");
  });
});

