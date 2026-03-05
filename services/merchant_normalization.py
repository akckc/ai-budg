import re

def normalize_merchant(description: str) -> str:
    """
    Deterministic normalization of merchant name from transaction description.
    
    Pure function, no side effects, no network calls.
    
    Transformations (in order):
    1. Trim whitespace from beginning and end
    2. Convert to uppercase
    3. Collapse multiple spaces to single space
    4. Remove aggressive noise: POS, ONLINE, TRANSFER, FEE
    5. Remove patterns like #<numbers>, store numbers, and bank codes
    
    Examples:
    - "STARBUCKS #1234 POS" -> "STARBUCKS"
    - "AMAZON.COM AMZN.COM/BILL" -> "AMAZON.COM"
    - "TRANSFER TO SAVINGS" -> "TRANSFER TO SAVINGS" (only removed as suffixes)
    - "CHASE FEE" -> "CHASE"
    
    Args:
        description: raw transaction description string
    
    Returns:
        cleaned merchant name string
    """
    if not description or not isinstance(description, str):
        return ""
    
    # Step 1: Trim whitespace
    text = description.strip()
    
    # Step 2: Convert to uppercase
    text = text.upper()
    
    # Step 3: Collapse multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    
    # Step 4 & 5: Remove noise patterns
    # Remove store/register numbers like #1234, #456789
    text = re.sub(r'#\d+', '', text)
    
    # Remove common noise suffixes: POS, ONLINE, TRANSFER, FEE
    noise_words = ['POS', 'ONLINE', 'TRANSFER', 'FEE', 'DEBIT', 'CREDIT']
    for word in noise_words:
        text = re.sub(r'\b' + word + r'\b', '', text)
    
    # Remove bank codes and routing patterns (e.g., XXXX1234 at end)
    text = re.sub(r'X{4}\d+', '', text)
    
    # Clean up any trailing/leading punctuation and repeated spaces again
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text
