pragma solidity >=0.7.0 <0.9.0;


import "./external/SPLToken.sol";


contract splTokenCaller {

    SPLToken constant _splToken = SPLToken(0xFf00000000000000000000000000000000000004);

    event LogBytes(bytes32 value);
    event LogStr(string value);

    function getMint(bytes32 _tokenMint) public returns (SPLToken.Mint memory){
        SPLToken.Mint memory m = _splToken.getMint(_tokenMint);
        return m;
    }

    function findAccount(address account) public returns (bytes32) {
        bytes32 _tokenMint = _splToken.findAccount(_salt(account));
        return _tokenMint;
    }

    function findAccount(bytes32 account) public returns (bytes32) {
        bytes32 _tokenMint = _splToken.findAccount(account);
        return _tokenMint;
    }

    function getAccount(bytes32 token_mint) public returns (SPLToken.Account memory){
        SPLToken.Account memory a = _splToken.getAccount(token_mint);
        return a;
    }

    function initializeMint(uint8 decimals) public {

        bytes32 mint = _splToken.initializeMint(bytes32(0), decimals);
        emit LogBytes(mint);
    }

    function initializeMint(bytes32 salt, uint8 decimals) public {

        bytes32 mint = _splToken.initializeMint(salt, decimals);
        emit LogBytes(mint);
    }

    function initializeAccount(address addr, bytes32 mint) public {
        _splToken.initializeAccount(_salt(addr), mint);

    }

    function mintTo(address to, uint amount, bytes32 tokenMint) public {
        bytes32 toSolana = _splToken.findAccount(_salt(to));

        _splToken.mintTo(tokenMint, toSolana, uint64(amount));
    }

    function transfer(address from, address to, uint amount) public {
        bytes32 fromSolana = _splToken.findAccount(_salt(from));
        bytes32 toSolana = _splToken.findAccount(_salt(to));

        _splToken.transfer(fromSolana, toSolana, uint64(amount));
    }

    function burn(bytes32 mint, address account, uint amount) public {
        bytes32 solAcc = _splToken.findAccount(_salt(account));

        _splToken.burn(mint, solAcc, uint64(amount));
    }

    function isSystemAccount(address account) public returns (bool) {
        bytes32 solAcc = _splToken.findAccount(_salt(account));
        return _splToken.isSystemAccount(solAcc);
    }

    function isSystemAccount(bytes32 addr) public returns (bool) {
        return _splToken.isSystemAccount(addr);
    }

    function closeAccount(address account) public {
        bytes32 solAcc = _splToken.findAccount(_salt(account));
        _splToken.closeAccount(solAcc);
    }

    function freeze(bytes32 mint, address account) public {
        bytes32 solAcc = _splToken.findAccount(_salt(account));
        _splToken.freeze(mint, solAcc);
    }

    function thaw(bytes32 mint, address account) public {
        bytes32 solAcc = _splToken.findAccount(_salt(account));

        _splToken.thaw(mint, solAcc);
    }

    function approve(address source, address target, uint64 amount) public {
        bytes32 fromSolana = _splToken.findAccount(_salt(source));
        bytes32 toSolana = _splToken.findAccount(_salt(target));
        _splToken.approve(fromSolana, toSolana, uint64(amount));
    }

    function revoke(address source) public {
        bytes32 fromSolana = _splToken.findAccount(_salt(source));
        _splToken.revoke(fromSolana);

    }

    function _salt(address account) internal pure returns (bytes32) {
        return bytes32(uint256(uint160(account)));
    }


}