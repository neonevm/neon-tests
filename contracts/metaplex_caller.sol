pragma solidity >=0.7.0 <0.9.0;

import "./external/Metaplex.sol";
import "./external/SPLToken.sol";

contract metaplexCaller {

    Metaplex constant _metaplex = Metaplex(0xff00000000000000000000000000000000000005);
    SPLToken constant _splToken = SPLToken(0xFf00000000000000000000000000000000000004);

    event LogBytes(bytes32 value);
    event LogStr(string value);

    function callCreateMetadata(bytes32 seed, string memory name, string memory symbol, string memory uri) public {
        bytes32 mintId = _splToken.initializeMint(seed, 0);

        bytes32 mint = _metaplex.createMetadata(mintId, name, symbol, uri);
        emit LogBytes(mintId);
    }

    function name(bytes32 mint) view public returns (string memory name){
        name = _metaplex.name(mint);
        return name;
    }

    function symbol(bytes32 mint) view public returns (string memory symbol){
        symbol = _metaplex.symbol(mint);
        return symbol;
    }

    function uri(bytes32 mint) view public returns (string memory uri){
        uri = _metaplex.uri(mint);
        return uri;
    }

    function isInitialized(bytes32 mint) view public returns (bool){
        return _metaplex.isInitialized(mint);
    }

    function isNFT(bytes32 mint) view public returns (bool){
        return _metaplex.isNFT(mint);
    }
}