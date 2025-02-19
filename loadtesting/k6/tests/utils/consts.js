import http from 'k6/http';

// Parse envs.json
const network = __ENV.K6_NETWORK;
const envConfig = JSON.parse(open("../../../../envs.json"));
if (network == undefined) {
    throw new Error("Network is not defined, please set K6_NETWORK env variable.");
}

let env;
switch (network) {
    case "local":
        env = envConfig.local;
        break;
    case "devnet":
        env = envConfig.devnet;
        break;
    default:
        env = envConfig.local;
}

// Set Chain Id
export const networkId = parseInt(env.network_ids.neon);

// Set Proxy URL
export const proxyUrl = env.proxy_url;

// Set Tracer URL
export const tracerUrl = env.tracer_url;

// Faucet URL
export let faucetUrl = env.faucet_url;
if (!faucetUrl.includes("request_neon")) {
    faucetUrl = http.url([faucetUrl, 'request_neon']);
}

// Accounts data
export const initialAccountBalance = parseInt(__ENV.K6_INITIAL_BALANCE);
export const usersNumber = parseInt(__ENV.K6_USERS_NUMBER);


// ERC20 contract data
export const erc20Address = __ENV.K6_ERC20_ADDRESS;

// Block contract data
export const BlockContractAddress = __ENV.K6_BLOCK_ADDRESS;

// Transfer amount range
export const transferAmountRange = [0.01, 0.02, 0.03, 0.04, 0.05];