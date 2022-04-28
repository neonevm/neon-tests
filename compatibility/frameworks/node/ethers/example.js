"use strict";
exports.__esModule = true;
var ethers_1 = require("ethers");
var provider = new ethers_1.ethers.providers.JsonRpcProvider("https://proxy.devnet.neonlabs.org/solana", 245022926);
var wallet = ethers_1.ethers.Wallet.createRandom();
// await axios.post("https://neonswap.live/request_neon", {
//     address: wallet.address,
//     amount: "1"
// });
