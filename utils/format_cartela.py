def format_cartela(cartela):
    """
    Formats a cartela (bingo card) into a readable string.
    """
    return "\n".join([" ".join(map(str, row)) for row in cartela])
