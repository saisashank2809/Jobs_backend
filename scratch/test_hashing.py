import sys
import os

# Add the project root to sys.path to import from app
sys.path.append(os.getcwd())

from app.utils.security import get_password_hash, verify_password

def test_hashing():
    password = "secret_password_123"
    
    print(f"Testing password: {password}")
    
    # Test hashing
    hashed = get_password_hash(password)
    print(f"Hashed password: {hashed}")
    
    assert hashed != password, "Hashed password should not be equal to plaintext"
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$"), "Bcrypt hash should start with $2b$ or $2a$"
    
    # Test verification
    is_valid = verify_password(password, hashed)
    print(f"Verification (correct password): {is_valid}")
    assert is_valid == True, "Verification should return True for correct password"
    
    is_invalid = verify_password("wrong_password", hashed)
    print(f"Verification (wrong password): {is_invalid}")
    assert is_invalid == False, "Verification should return False for wrong password"
    
    print("\nAll hashing tests passed!")

if __name__ == "__main__":
    test_hashing()
