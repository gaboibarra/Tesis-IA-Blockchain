// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TxRegistry {
    /// @notice Evento sin PII; solo IDs/hashes y timestamp de bloque.
    event SecureTx(bytes32 decisionId, bytes32 txRefHash, uint256 ts);

    /// @notice Emite un evento para transacción segura (idempotente a nivel app).
    function registerSecureTx(bytes32 decisionId, bytes32 txRefHash) external {
        emit SecureTx(decisionId, txRefHash, block.timestamp);
    }
}
