const { ethers } = require("hardhat");

async function main() {
  console.log("Starting deployment of PatientRecord contract...");

  const PatientRecord = await ethers.getContractFactory("PatientRecord");
  const patientRecord = await PatientRecord.deploy();

  await patientRecord.waitForDeployment();

  const address = await patientRecord.getAddress();
  console.log(`\n✅ PatientRecord deployed to: ${address}`);
  console.log(`\nNext Step: Add this address as 'CONTRACT_ADDRESS' in your Railway Backend variables.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
