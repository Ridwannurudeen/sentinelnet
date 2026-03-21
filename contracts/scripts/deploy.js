const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Balance:", hre.ethers.formatEther(balance), "ETH");

  const Factory = await hre.ethers.getContractFactory("SentinelNetStaking");
  const contract = await Factory.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log("SentinelNetStaking deployed to:", address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
