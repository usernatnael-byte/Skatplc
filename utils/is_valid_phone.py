def is_valid_tx_id(tx_id):
    """
    Validates a transaction ID format.
    Must be a non-empty string starting with 'TX' and at least 6 characters.
    """
    if not isinstance(tx_id, str):
        return False
    if not tx_id.startswith("TX"):
        return False
    if len(tx_id) < 6:
        return False
    return tx_id.isalnum()
