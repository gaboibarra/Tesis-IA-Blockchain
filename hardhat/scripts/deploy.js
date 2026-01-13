const fs = require("fs");
const path = require("path");
require("dotenv").config();
const { ethers } = require("hardhat");

function writeFileSafe(p, content) {
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, content, { encoding: "utf-8" });
}
function updateEnvContractAddress(envPath, address) {
  let text = fs.readFileSync(envPath, "utf-8");
  if (text.includes("CONTRACT_ADDRESS=")) {
    text = text.replace(/CONTRACT_ADDRESS=.*/g, `CONTRACT_ADDRESS=${address}`);
  } else {
    if (!text.endsWith("\n")) text += "\n";
    text += `CONTRACT_ADDRESS=${address}\n`;
  }
  fs.writeFileSync(envPath, text, { encoding: "utf-8" });
}

async function main() {
  // __dirname = .../hardhat/scripts, el .env está en la raíz del proyecto
  const envProject = path.resolve(__dirname, "..", "..", ".env");

  const provider = new ethers.JsonRpcProvider(process.env.RPC_URL || "http://127.0.0.1:8545");
  let signer;
  if (process.env.PRIVATE_KEY && process.env.PRIVATE_KEY.startsWith("0x") && process.env.PRIVATE_KEY.length === 66) {
    signer = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
  } else {
    [signer] = await ethers.getSigners(); // Ganache signer
  }

  const factory = await ethers.getContractFactory("TxRegistry", signer);
  const contract = await factory.deploy();
  await contract.waitForDeployment();

  const address = await contract.getAddress();
  console.log(`TxRegistry deployed at: ${address}`);

  // ABI desde artifacts
  const artifactPath = path.resolve(__dirname, "..", "artifacts", "contracts", "TxRegistry.sol", "TxRegistry.json");
  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf-8"));
  const abi = JSON.stringify(artifact.abi, null, 2);

  // Guardar ABI y address en /abi (raíz del proyecto)
  const abiDir = path.resolve(__dirname, "..", "..", "abi");
  writeFileSafe(path.join(abiDir, "TxRegistry.json"), abi);
  writeFileSafe(path.join(abiDir, "TxRegistry.address"), address);

  // Actualizar .env
  updateEnvContractAddress(envProject, address);
  console.log("ABI y address exportados, .env actualizado.");
}

main().catch((e) => { console.error(e); process.exit(1); });
