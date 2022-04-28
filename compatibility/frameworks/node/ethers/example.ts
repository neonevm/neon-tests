import { ethers } from "ethers";
import axios from "axios";
import {
    TransactionRequest
} from "@ethersproject/abstract-provider";

// const provider = new ethers.providers.JsonRpcProvider("https://proxy.devnet.neonlabs.org/solana", 245022926);
const provider = new ethers.providers.JsonRpcProvider("http://proxy.night.stand.neontest.xyz/solana", 111);
const wallet = ethers.Wallet.fromMnemonic("build fruit nerve useless keep clean zero drop garden stairs matrix chicken").connect(provider);

const contractBytecode = '60806040526000805534801561001457600080fd5b50610504806100246000396000f3fe608060405234801561001057600080fd5b50600436106100625760003560e01c806306661abd1461006757806308650c7a1461008557806308cf31ed146100a1578063371303c0146100bd5780636d4ce63c146100c7578063b3bcfa82146100e5575b600080fd5b61006f6100ef565b60405161007c91906101a2565b60405180910390f35b61009f600480360381019061009a9190610317565b6100f5565b005b6100bb60048036038101906100b6919061038c565b6100fe565b005b6100c561014a565b005b6100cf610165565b6040516100dc91906101a2565b60405180910390f35b6100ed61016e565b005b60005481565b60008190505050565b60008290505b81831015610122578080610117906103fb565b915050809250610104565b600181836101309190610444565b1415610145578080610141906103fb565b9150505b505050565b600160008082825461015c9190610478565b92505081905550565b60008054905090565b60016000808282546101809190610444565b92505081905550565b6000819050919050565b61019c81610189565b82525050565b60006020820190506101b76000830184610193565b92915050565b6000604051905090565b600080fd5b600080fd5b600080fd5b600080fd5b6000601f19601f8301169050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b610224826101db565b810181811067ffffffffffffffff82111715610243576102426101ec565b5b80604052505050565b60006102566101bd565b9050610262828261021b565b919050565b600067ffffffffffffffff821115610282576102816101ec565b5b61028b826101db565b9050602081019050919050565b82818337600083830152505050565b60006102ba6102b584610267565b61024c565b9050828152602081018484840111156102d6576102d56101d6565b5b6102e1848285610298565b509392505050565b600082601f8301126102fe576102fd6101d1565b5b813561030e8482602086016102a7565b91505092915050565b60006020828403121561032d5761032c6101c7565b5b600082013567ffffffffffffffff81111561034b5761034a6101cc565b5b610357848285016102e9565b91505092915050565b61036981610189565b811461037457600080fd5b50565b60008135905061038681610360565b92915050565b600080604083850312156103a3576103a26101c7565b5b60006103b185828601610377565b92505060206103c285828601610377565b9150509250929050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b600061040682610189565b91507fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff821415610439576104386103cc565b5b600182019050919050565b600061044f82610189565b915061045a83610189565b92508282101561046d5761046c6103cc565b5b828203905092915050565b600061048382610189565b915061048e83610189565b9250827fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff038211156104c3576104c26103cc565b5b82820190509291505056fea264697066735822122063f761279df8b25435b65ba1310b4a70b633063b0c80c733284fd95db409a5e464736f6c634300080a0033'
const contractABI = [{'inputs': [{'internalType': 'string', 'name': 'text', 'type': 'string'}], 'name': 'bigString', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'}, {'inputs': [], 'name': 'count', 'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [], 'name': 'dec', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'}, {'inputs': [], 'name': 'get', 'outputs': [{'internalType': 'uint256', 'name': '', 'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}, {'inputs': [], 'name': 'inc', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'}, {'inputs': [{'internalType': 'uint256', 'name': 'x', 'type': 'uint256'}, {'internalType': 'uint256', 'name': 'y', 'type': 'uint256'}], 'name': 'moreInstruction', 'outputs': [], 'stateMutability': 'nonpayable', 'type': 'function'}]
const contractFactory = new ethers.ContractFactory(contractABI, contractBytecode, wallet);


async function exampleContract() {
    // const contractTx = await contractFactory.getDeployTransaction()
    // const deployTx: TransactionRequest = {
    //     "nonce": await provider.getTransactionCount(wallet.address),
    //     "gasPrice": await provider.getGasPrice(),
    //     "from": wallet.address,
    //     "data": contractTx.data
    // }
    // deployTx["gasLimit"] = await provider.estimateGas(deployTx);
    //
    // const signed = await wallet.signTransaction(deployTx);
    // const tx = await provider.sendTransaction(signed);
    // console.log(tx);
    // const receipt = await tx.wait();
    // console.log(receipt);
    //
    // const contract = contractFactory.attach(receipt.contractAddress).connect(provider);
    // console.log(await contract.get());
    await provider.getBlock("latest");
    // const deployTx = await contractFactory.deploy();
    // console.log(deployTx);

}

exampleContract().then(() => {
    console.log("done");
});