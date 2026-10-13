const { ethers } = require("hardhat");

async function main() {
  console.log("Starting deployment of PatientRecord contract...");

  const [deployer] = await ethers.getSigners();
  console.log(`Deployer address: ${deployer.address}`);

  const PatientRecord = await ethers.getContractFactory("PatientRecord");
  const patientRecord = await PatientRecord.deploy();

  const deployTx = patientRecord.deploymentTransaction();
  console.log(`Deployment transaction broadcast: ${deployTx.hash}`);
  console.log(`Etherscan Tx: https://sepolia.etherscan.io/tx/${deployTx.hash}`);

  await patientRecord.waitForDeployment();

  const address = await patientRecord.getAddress();
  console.log(`\nPatientRecord deployed to: ${address}`);
  console.log(`Etherscan Contract: https://sepolia.etherscan.io/address/${address}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
