// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {ISPLTokenProgram} from "../../external/neon-contracts/contracts/precompiles/ISPLTokenProgram.sol";
import {IMetaplexProgram} from "../../external/neon-contracts/contracts/precompiles/IMetaplexProgram.sol";
import {ICallSolana} from "../../external/neon-contracts/contracts/precompiles/ICallSolana.sol";

import {ISolanaNative} from "../../external/neon-contracts/contracts/precompiles/ISolanaNative.sol";
import {QueryAccount} from "../../external/neon-contracts/contracts/precompiles/QueryAccount.sol";


/// @title ERC20ForSplBackbone
/// @author https://twitter.com/mnedelchev_
/// @notice This contract serves as a backbone contract for both ERC20ForSpl and ERC20ForSplMintable smart contracts. It
/// provides a standard ERC20 interface supplemented with custom functions and variables providing compatibility with
/// Solana's SPL Token. This allows NeonEVM users and dApps to interact with ERC20 tokens deployed on NeonEVM as well as
/// native Solana SPL tokens.
contract ERC20ForSplBackbone {
    /// @dev Instance of NeonEVM's SPLTokenProgram precompiled smart contract
    ISPLTokenProgram public constant SPLTOKEN_PROGRAM = ISPLTokenProgram(0xFf00000000000000000000000000000000000004);
    /// @dev Instance of NeonEVM's MetaplexProgram precompiled smart contract
    IMetaplexProgram public constant METAPLEX_PROGRAM = IMetaplexProgram(0xff00000000000000000000000000000000000005);
    /// @dev Instance of NeonEVM's CallSolana precompiled smart contract
    ICallSolana public constant CALL_SOLANA = ICallSolana(0xFF00000000000000000000000000000000000006);
    /// @dev Instance of NeonEVM's SolanaNative precompiled smart contract
    ISolanaNative public constant SOLANA_NATIVE = ISolanaNative(0xfF00000000000000000000000000000000000007);
    /// @dev Hex-encoding of Solana's base58-encoded Program id 53DfF883gyixYNXnM7s5xhdeyV8mVk9T4i2hGV9vG9io
    bytes32 public constant NEON_EVM_PROGRAM = 0x3c00392b787d38a853d124057634c43c7133c612461d74feb17f4248155286c0;
    /// @dev Hex-encoding of Solana's base58-encoded Token program id TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA
    bytes32 public constant TOKEN_PROGRAM_ID = 0x06ddf6e1d765a193d9cbe146ceeb79ac1cb485ed5f5b37913a8cf5857eff00a9;
    /// @dev Hex-encoding of Solana's base58-encoded Associated Token program id ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL
    bytes32 public constant ASSOCIATED_TOKEN_PROGRAM_ID = 0x8c97258f4e2489f1bb3d1029148e0d830b5a1399daff1084048e7bd8dbe9f859;
    /// @dev Solana SPL Token address
    bytes32 immutable public tokenMint;
    /// @dev ERC20 allowances mapping
    mapping(address => mapping(address => uint256)) private _allowances;

    /// @dev ERC20 Transfer event
    event Transfer(address indexed from, address indexed to, uint256 amount);
    /// @dev ERC20 Approval event
    event Approval(address indexed owner, address indexed spender, uint256 amount);
    /// @dev Special event for SPL Token approval of a Solana account
    event ApprovalSolana(address indexed owner, bytes32 indexed spender, uint64 amount);
    /// @dev Special event for SPL Token transfer to a Solana account
    event TransferSolana(address indexed from, bytes32 indexed to, uint64 amount);

    /// @notice Passed EVM address is empty.
    error EmptyAddress();
    /// @notice Passed SVM account is empty.
    error EmptyAccount();
    /// @notice Spending more than the allowed amount.
    error InvalidAllowance();
    /// @notice Requested amount higher than the actual balance.
    error AmountExceedsBalance();
    /// @notice The token mint on Solana has no metadata stored in the Metaplex program.
    error MissingMetaplex();
    /// @notice The token mint on Solana is invalid.
    error InvalidTokenMint();
    /// @notice Invalid token amount.
    error AmountExceedsUint64();

    /// @notice Token name getter function
    /// @return The name of the SPLToken fetched from Solana's Metaplex program.
    function name() public view returns (string memory) {
        return METAPLEX_PROGRAM.name(tokenMint);
    }

    /// @notice Token symbol getter function
    /// @return The token symbol fetched from Solana's Metaplex program.
    function symbol() public view returns (string memory) {
        return METAPLEX_PROGRAM.symbol(tokenMint);
    }

    /// @notice Token decimals getter function
    /// @return The token decimals fetched from Solana's SPL Token program.
    function decimals() public view returns (uint8) {
        return SPLTOKEN_PROGRAM.getMint(tokenMint).decimals;
    }

    /// @notice Token supply getter function
    /// @return The token supply fetched from Solana's SPL Token program.
    function totalSupply() public view returns (uint256) {
        return SPLTOKEN_PROGRAM.getMint(tokenMint).supply;
    }

    /// @notice Token balance getter function
    /// @param account The NeonEVM address to get the balance of
    /// @return The account's spendable token balance fetched from Solana's SPL Token program.
    /// @dev While the ERC20 standard uses a mapping to store balances, Solana's SPL Token standard stores token
    /// balances along with other token-related data on individual token accounts.
    ///
    /// NeonEVM uses an arbitrary token account on Solana (32 bytes address returned by the `solanaAccount(address)`
    /// function) to store a user's token balance. We first fetch the token balance stored on this account.
    ///
    /// The SPL Token program uses an associated token account (ATA) derived from a user's native Solana account to store
    /// a user's token balance. In the case where the `account` address refers to a native Solana account (32 bytes
    /// address returned by the `SOLANA_NATIVE.solanaAddress(account)` function) we also fetch the token balance stored
    /// in the associated token account (ATA) derived from this Solana account (32 bytes address returned by the
    /// `getTokenMintATA(bytes32)` function. However, this ATA balance is only spendable if the `account`'s external
    /// authority has been set as the delegate of the ATA, in which case it is added to the spendable token balance.
    function balanceOf(address account) public view returns (uint256) {
        uint balance = SPLTOKEN_PROGRAM.getAccount(solanaAccount(account)).amount;

        (bytes32 ataAccount, uint64 ataBalance) = _getSolanaATA(account, false);
        if (ataAccount != bytes32(0)) {
            balance += ataBalance;
        }
        return balance;
    }

    /// @notice Token ERC20 allowance getter function
    /// @return The ERC20 allowance provided by the `owner` to the `spender`
    function allowance(address owner, address spender) public view returns (uint256) {
        return _allowances[owner][spender];
    }

    /// @notice ERC20 approve function
    /// @custom:getter allowance
    function approve(address spender, uint256 amount) public returns (bool) {
        require(spender != address(0), EmptyAddress());

        _approve(msg.sender, spender, amount);
        return true;
    }

    /// @notice ERC20 transfer function
    /// @custom:getter balanceOf
    function transfer(address to, uint256 amount) public returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    /// @notice ERC20 transferFrom function: spends the ERC20 allowance provided by the `from` account to `msg.sender`
    /// @custom:getter balanceOf
    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(from != address(0), EmptyAddress());

        _spendAllowance(from, msg.sender, amount);
        _transfer(from, to, amount);
        return true;
    }

    /// @notice ERC20 burn function
    /// @custom:getter balanceOf
    function burn(uint256 amount) public returns (bool) {
        _burn(msg.sender, amount);
        return true;
    }

    /// @notice ERC20 burnFrom function: spends the ERC20 allowance provided by the `from` account to `msg.sender`
    /// @custom:getter balanceOf
    function burnFrom(address from, uint256 amount) public returns (bool) {
        require(from != address(0), EmptyAddress());

        _spendAllowance(from, msg.sender, amount);
        _burn(from, amount);
        return true;
    }

    /// @notice Custom ERC20ForSPL function: provides SPL Token delegation to a Solana account.
    /// @dev SPL Token delegation is similar to an ERC20 allowance but it is not stored in the ERC20 `_allowances`
    /// mapping.
    ///
    /// The SPL Token standard's concept of 'delegation' differs from ERC20 'allowances' in that it is only possible to
    /// delegate to one single Solana account and subsequent delegations will erase previous delegations.
    /// @param spender The 32 bytes address of the delegate account, i.e. the Solana account to be approved
    /// @param amount The amount to be delegated to the delegate
    /// @custom:getter getAccountDelegateData
    function approveSolana(bytes32 spender, uint64 amount) public returns (bool) {
        require(spender != bytes32(0), EmptyAccount());

        bytes32 fromSolana = solanaAccount(msg.sender);
        if (amount > 0) {
            SPLTOKEN_PROGRAM.approve(fromSolana, spender, amount);
        } else {
            SPLTOKEN_PROGRAM.revoke(fromSolana);
        }

        emit Approval(msg.sender, address(0), amount);
        emit ApprovalSolana(msg.sender, spender, amount);
        return true;
    }

    /// @notice Custom ERC20ForSPL function: transfers to a Solana SPL Token account
    /// @param to The 32 bytes SPL Token account address of the recipient
    /// @param amount The amount to be transferred to the recipient
    /// @custom:getter balanceOf
    function transferSolana(bytes32 to, uint64 amount) public returns (bool) {
        return _transferSolana(msg.sender, to, amount);
    }

    /// @notice Custom ERC20ForSPL function: spends the ERC20 allowance provided by the `from` account to `msg.sender` by
    /// transferring to a Solana SPL Token account
    /// @param to The 32 bytes SPL Token account address of the recipient
    /// @custom:getter balanceOf
    function transferSolanaFrom(address from, bytes32 to, uint64 amount) public returns (bool) {
        require(from != address(0), EmptyAddress());

        _spendAllowance(from, msg.sender, amount);
        return _transferSolana(from, to, amount);
    }

    /// @notice Custom ERC20ForSPL function: spends the SPL Token delegation provided by the `from` Solana SPL Token
    /// account to the external authority of NeonEVM arbitrary token account attributed to `msg.sender`
    /// @param from The 32 bytes SPL Token account address which provided delegation to the external authority of
    /// NeonEVM arbitrary token account attributed to `msg.sender`
    /// @param amount The amount to be transferred to the NeonEVM arbitrary token account attributed to `msg.sender`
    /// @custom:getter balanceOf
    function claim(bytes32 from, uint64 amount) external returns (bool) {
        return claimTo(from, msg.sender, amount);
    }

    /// @notice Custom ERC20ForSPL function: spends the SPL Token delegation provided by the `from` Solana SPL Token
    /// account to the external authority of NeonEVM arbitrary token account attributed to `msg.sender` and transfers to
    /// the NeonEVM arbitrary token account attributed to the `to` address
    /// @param from The 32 bytes SPL Token account address which provided delegation to the external authority of
    /// NeonEVM arbitrary token account attributed to `msg.sender`
    /// @param to The NeonEVM address of the recipient
    /// @param amount The amount to be transferred to the NeonEVM arbitrary token account attributed to the `to` address
    /// @custom:getter balanceOf
    function claimTo(bytes32 from, address to, uint64 amount) public returns (bool) {
        require(to != address(0), EmptyAddress());
        bytes32 toSolana = solanaAccount(to);
        require(SPLTOKEN_PROGRAM.getAccount(from).amount >= amount, AmountExceedsBalance());

        if (SPLTOKEN_PROGRAM.isSystemAccount(toSolana)) {
            SPLTOKEN_PROGRAM.initializeAccount(_salt(to), tokenMint);
        }

        SPLTOKEN_PROGRAM.transferWithSeed(_salt(msg.sender), from, toSolana, amount);
        emit Transfer(address(0), to, amount);
        return true;
    }

    /// @notice Internal function to update the `_allowances` mapping when a new ERC20 approval is provided
    function _approve(address owner, address spender, uint256 amount) internal {
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }

    /// @notice Internal function to update the `_allowances` mapping when an ERC20 allowance is spent
    function _spendAllowance(address owner, address spender, uint256 amount) internal {
        uint256 currentAllowance = _allowances[owner][spender];
        if (currentAllowance != type(uint256).max) {
            require(currentAllowance >= amount, InvalidAllowance());
            _approve(owner, spender, currentAllowance - amount);
        }
    }

    /// @notice Internal function to burn tokens
    function _burn(address from, uint256 amount) internal {
        require(amount <= type(uint64).max, AmountExceedsUint64());
        bytes32 fromSolana = solanaAccount(from);
        require(SPLTOKEN_PROGRAM.getAccount(fromSolana).amount >= amount, AmountExceedsBalance());

        SPLTOKEN_PROGRAM.burn(tokenMint, fromSolana, uint64(amount));

        emit Transfer(from, address(0), amount);
    }

    /// @notice Internal function to transfer tokens
    function _transfer(address from, address to, uint256 amount) internal {
        require(to != address(0), EmptyAddress());
        require(amount <= type(uint64).max, AmountExceedsUint64());

        // First we get the token balance of NeonEVM's arbitrary token account associated to the `from` address
        bytes32 fromSolanaPDA = solanaAccount(from);
        uint64 pdaBalance = SPLTOKEN_PROGRAM.getAccount(fromSolanaPDA).amount;
        // In the case where this balance is not enough to cover the transfer `amount`, and if the `from` address
        // refers to a native Solana account, we also fetch the token balance stored in the associated token account
        // (ATA) derived from this Solana account. However, this ATA balance is only spendable if the external authority
        // of the `from` address has been set as the delegate of the ATA, in which case it is added to the available ATA
        // token balance.
        bytes32 fromSolanaATA;
        uint64 availableATABalance;
        if (pdaBalance < amount) {
            (bytes32 ataAccount, uint64 ataBalanceFrom) = _getSolanaATA(from, false);
            if (ataAccount != bytes32(0)) {
                fromSolanaATA = ataAccount;
                availableATABalance += ataBalanceFrom;
            }
        }

        if (pdaBalance + availableATABalance < amount) revert AmountExceedsBalance();

        // If the `to` address refers to a native Solana account, we transfer to the associated token account (ATA)
        // derived from this Solana account. Otherwise, we transfer to NeonEVM's arbitrary token account associated to
        // the `to` address
        bytes32 toSolana;
        (bytes32 ataAccountTo,) = _getSolanaATA(to, true);
        if (ataAccountTo != bytes32(0)) {
            toSolana = ataAccountTo;
        } else {
            toSolana = solanaAccount(to);
        }

        // If the recipient Solana account is not an initialized token account, we initialize it first
        if (SPLTOKEN_PROGRAM.isSystemAccount(toSolana)) {
            SPLTOKEN_PROGRAM.initializeAccount(_salt(to), tokenMint);
        }

        // The balance of NeonEVM's arbitrary token account associated to the `from` address is spent in priority. Then,
        // if the `from` address refers to a native Solana account, the available balance stored in the associated token
        // account (ATA) derived from this Solana account is spent
        uint64 amountFromPDA = (uint64(amount) > pdaBalance) ? pdaBalance : uint64(amount);
        uint64 amountFromATA = uint64(amount) - amountFromPDA;

        if (amountFromPDA != 0) {
            SPLTOKEN_PROGRAM.transfer(fromSolanaPDA, toSolana, amountFromPDA);
        }

        if (amountFromATA != 0) {
            SPLTOKEN_PROGRAM.transferWithSeed(_salt(from), fromSolanaATA, toSolana, amountFromATA);
        }

        emit Transfer(from, to, amount);
    }

    /// @notice Internal function to transfer tokens to a Solana SPL Token account
    function _transferSolana(address from, bytes32 to, uint64 amount) internal returns (bool) {
        require(to != bytes32(0), EmptyAccount());
        bytes32 fromSolana = solanaAccount(from);
        require(SPLTOKEN_PROGRAM.getAccount(fromSolana).amount >= amount, AmountExceedsBalance());

        SPLTOKEN_PROGRAM.transfer(fromSolana, to, uint64(amount));

        emit Transfer(from, address(0), amount);
        emit TransferSolana(from, to, amount);
        return true;
    }

    /// @notice Custom ERC20ForSPL getter function
    /// @return The NeonEVM arbitrary token account attributed to the 'account` address
    function solanaAccount(address account) public pure returns (bytes32) {
        return SPLTOKEN_PROGRAM.findAccount(_salt(account));
    }

    /// @notice Custom ERC20ForSPL getter function
    /// @return The 32 bytes Solana SPL Token account address of the delegate and the amount that was delegated to that
    // delegate  by the NeonEVM arbitrary token account attributed to the `account` address.
    ///
    /// Returned data corresponds to SPL Token delegation only and does not include any ERC20 allowances provided by
    /// the `account` address.
    function getAccountDelegateData(address account) public view returns(bytes32, uint64) {
        ISPLTokenProgram.Account memory tokenAccount = SPLTOKEN_PROGRAM.getAccount(solanaAccount(account));
        return (tokenAccount.delegate, tokenAccount.delegated_amount);
    }

    /// @notice Custom ERC20ForSPL getter function
    /// @return The SPL Token associated token account (ATA) address for this contract's `tokenMint` and provided Solana
    /// account address
    /// @param account 32 bytes Solana account address
    function getTokenMintATA(bytes32 account) public view returns(bytes32) {
        return CALL_SOLANA.getSolanaPDA(
            ASSOCIATED_TOKEN_PROGRAM_ID,
            abi.encodePacked(
                account,
                TOKEN_PROGRAM_ID,
                tokenMint
            )
        );
    }

    /// @notice Custom ERC20ForSPL getter function
    /// @return The 'external authority' Solana account which must be set as the delegate of a Solana token account such
    /// that the NeonEVM `account` passed as argument to the `getUserExtAuthority` function can call the `claim` or
    /// `claimTo` function to transfer tokens from the delegated Solana token account.
    /// @dev In the case where the `account` address refers to a native Solana account (32 bytes address returned by the
    /// `SOLANA_NATIVE.solanaAddress(account)` function) any token amount delegated by the native Solana account's ATA
    /// to this external authority is transferable using the `transfer` function and is added to the `account` balance
    /// returned by the `balanceOf` function.
    function getUserExtAuthority(address account) public view returns(bytes32) {
        return CALL_SOLANA.getSolanaPDA(
            NEON_EVM_PROGRAM,
            abi.encodePacked(
                hex"03",
                hex"41555448", // AUTH
                address(this),
                _salt(account)
            )
        );
    }

    /// @return The 32 bytes public key of the Solana SPL associated token account (ATA) owned by the Solana account
    /// associated to the NeonEVM `account` address, and the ATA balance that is delegated to the external authority of
    /// the _NeonEVM_ `account`. If `skipDelegateCheck` is set to `true` then the returned delegated ATA balance is `0`.
    /// If the Solana account associated to the NeonEVM `account` has not been registered into NeonEVM the function will
    /// return `(bytes32(0), 0)`.
    function _getSolanaATA(address account, bool skipDelegateCheck) internal view returns(bytes32, uint64) {
        bytes32 solanaAddress = SOLANA_NATIVE.solanaAddress(account);

        if (solanaAddress != bytes32(0)) {
            bytes32 tokenMintATA = getTokenMintATA(solanaAddress);
            if (!SPLTOKEN_PROGRAM.isSystemAccount(tokenMintATA)) {
                ISPLTokenProgram.Account memory tokenMintATAData = SPLTOKEN_PROGRAM.getAccount(tokenMintATA);
                if (skipDelegateCheck || tokenMintATAData.delegate == getUserExtAuthority(account)) {
                    return (
                        tokenMintATA,
                        (tokenMintATAData.delegated_amount > tokenMintATAData.amount) ? tokenMintATAData.amount : tokenMintATAData.delegated_amount
                    );
                }
            }
        }
        return (bytes32(0), 0);
    }

    /// @return A 32 bytes salt used to derive the NeonEVM arbitrary token account attributed to the `account` address
    function _salt(address account) internal pure returns (bytes32) {
        return bytes32(uint256(uint160(account)));
    }
}

/// @title ERC20ForSpl
/// @author https://twitter.com/mnedelchev_
/// @notice This contract serves as an interface to interact with already deployed, native SPL Token on Solana.
contract ERC20ForSpl is ERC20ForSplBackbone {
    /// @param _tokenMint The 32 bytes Solana address of the underlying SPL Token
    constructor(bytes32 _tokenMint) {
        require(SPLTOKEN_PROGRAM.getMint(_tokenMint).isInitialized, InvalidTokenMint());
        require(METAPLEX_PROGRAM.isInitialized(_tokenMint), MissingMetaplex());

        tokenMint = _tokenMint;
    }
}

/// @title ERC20ForSplMintable
/// @author https://twitter.com/mnedelchev_
/// @notice This contract deploys a new SPL Token on Solana and give its administrator permission to mint new tokens
contract ERC20ForSplMintable is ERC20ForSplBackbone {
    address immutable _admin;

    /// @param _name The name of the SPL Token to be deployed
    /// @param _symbol The symbol of the SPL Token  to be deployed
    /// @param _decimals The decimals of the SPL Token to be deployed. This value cannot be bigger than 9 because of
    /// Solana's maximum value limit of uint64
    /// @param _owner The owner of the ERC20ForSplMintable contract which has the permissions to mint new tokens
    constructor(
        string memory _name,
        string memory _symbol,
        uint8 _decimals,
        address _owner
    ) {
        require(_decimals <= 9, InvalidDecimals());
        require(_owner != address(0), EmptyAddress());

        _admin = _owner;
        tokenMint = SPLTOKEN_PROGRAM.initializeMint(bytes32(0), _decimals);
        require(SPLTOKEN_PROGRAM.getMint(tokenMint).isInitialized, InvalidTokenMint());

        METAPLEX_PROGRAM.createMetadata(tokenMint, _name, _symbol, "");
        require(METAPLEX_PROGRAM.isInitialized(tokenMint), MissingMetaplex());
    }

    /// @notice Unauthorized msg.sender.
    error InvalidOwner();

    /// @notice Invalid token decimals. SPLToken program on Solana operates with u64 regarding the token balances.
    error InvalidDecimals();

    /// @return The 32 bytes Solana address of the underlying SPL Token
    function findMintAccount() public pure returns (bytes32) {
        return SPLTOKEN_PROGRAM.findAccount(bytes32(0));
    }

    /// @notice Mints new tokens to the NeonEVM arbitrary token account attributed to the 'to` address.
    /// @custom:getter balanceOf
    function mint(address to, uint256 amount) public {
        require(msg.sender == _admin, InvalidOwner());
        require(to != address(0), EmptyAddress());
        require(totalSupply() + amount <= type(uint64).max, AmountExceedsUint64());

        bytes32 toSolana = solanaAccount(to);
        if (SPLTOKEN_PROGRAM.isSystemAccount(toSolana)) {
            SPLTOKEN_PROGRAM.initializeAccount(_salt(to), tokenMint);
        }

        SPLTOKEN_PROGRAM.mintTo(tokenMint, toSolana, uint64(amount));
        emit Transfer(address(0), to, amount);
    }
}
