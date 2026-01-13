// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TxRegistry {
    /// @notice Evento sin PII; solo IDs/hashes y timestamp.
    event SecureTx(bytes32 decisionId, bytes32 txRefHash, uint256 ts);

    /// @notice Emite el evento para transacci?n segura.
    function registerSecureTx(bytes32 decisionId, bytes32 txRefHash) external {
        emit SecureTx(decisionId, txRefHash, block.timestamp);
    }
}
