from passlib.context import CryptContext

# 1. We add 'bcrypt__truncate_error=False' to KILL the 72-byte error message.
# 2. We add 'argon2' as the primary scheme for new passwords.
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"], 
    deprecated="auto",
    bcrypt__truncate_error=False 
)

def hash_password(password: str):
    # This will now use Argon2 (no length limit) for all NEW passwords
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    # This will check Bcrypt hashes (without crashing) AND Argon2 hashes
    return pwd_context.verify(plain_password, hashed_password)