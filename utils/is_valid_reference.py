def is_valid_reference(ref):
    """
    Validates deposit reference codes.
    Must be a non-empty alphanumeric string, at least 6 characters.
    """
    return isinstance(ref, str) and ref.isalnum() and len(ref) >= 6
