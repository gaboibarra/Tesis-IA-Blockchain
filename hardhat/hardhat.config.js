require("dotenv").config();
require("@nomicfoundation/hardhat-ethers");

const RPC_URL = process.env.RPC_URL || "http://127.0.0.1:8545";
const CHAIN_ID = Number(process.env.CHAIN_ID || 1337);

module.exports = {
  solidity: "0.8.20",
  networks: {
    localhost: { url: RPC_URL, chainId: CHAIN_ID }
  }
};
