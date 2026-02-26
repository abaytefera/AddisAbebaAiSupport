from passlib.context import CryptContext

# bcrypt ሲጠቀሙ የ 72 bytes ገደብ እንዳይመጣ ጥንቃቄ ማድረግ ይገባል
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    # ገደቡን ለማለፍ ርዝመቱን እዚህ ጋር ቼክ እናድርግ
    if len(password.encode('utf-8')) > 71:
        password = password[:71]
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    if len(plain_password.encode('utf-8')) > 71:
        plain_password = plain_password[:71]
    return pwd_context.verify(plain_password, hashed_password)