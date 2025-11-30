import re
from datetime import datetime
from functools import wraps
from fastapi import HTTPException
from typing import Dict, Any, List

def is_valid_email(email: str) -> bool:
    if not email:
        return False
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def is_valid_phone(phone: str) -> bool:
    if not phone:
        return False
    pattern = r'^01[0-9]\d{8}$'
    return re.match(pattern, phone) is not None

def is_valid_birth_year(year: int) -> bool:
    try:
        year = int(year)
        current_year = datetime.now().year
        return 1900 <= year <= current_year
    except (ValueError, TypeError):
        return False

def is_valid_password(password: str) -> tuple[bool, str]:
    if not password:
        return False, "비밀번호를 입력해주세요."
    if len(password) < 8:
        return False, "비밀번호는 최소 8자 이상이어야 합니다."
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        return False, "비밀번호가 너무 깁니다. (최대 72바이트, 한글 기준 약 24자)"
    return True, "유효한 비밀번호입니다."

def is_valid_name(name: str) -> tuple[bool, str]:
    if not name:
        return False, "이름을 입력해주세요."
    if len(name.strip()) < 2:
        return False, "이름은 최소 2자 이상이어야 합니다."
    if len(name) > 50:
        return False, "이름은 50자를 초과할 수 없습니다."
    return True, "유효한 이름입니다."

def is_valid_gender(gender: str) -> bool:
    valid_genders = ['남성', '여성', 'male', 'female', 'M', 'F']
    return gender in valid_genders

def is_valid_blood_type(blood_type: str) -> bool:
    valid_types = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
    return blood_type in valid_types

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> tuple[bool, str]:
    missing_fields = []
    for field in required_fields:
        if field not in data or not data[field]:
            missing_fields.append(field)
    
    if missing_fields:
        return False, f"다음 필드들이 필수입니다: {', '.join(missing_fields)}"
    return True, "모든 필수 필드가 입력되었습니다."

def create_error_response(message: str, status_code: int = 400) -> Dict[str, Any]:
    return {
        'success': False,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }

def create_success_response(message: str, data: Any = None) -> Dict[str, Any]:
    response = {
        'success': True,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }
    if data:
        response['data'] = data
    return response

def validate_json_request(f):
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        if not request.is_json:
            return create_error_response("JSON 형식의 요청이 필요합니다.")
        
        try:
            data = await request.get_json()
            if not data:
                return create_error_response("빈 JSON 데이터입니다.")
        except Exception as e:
            return create_error_response(f"JSON 파싱 오류: {str(e)}")
            
        return await f(*args, **kwargs)
    return decorated_function

def sanitize_string(text: str, max_length: int = None) -> str:
    if not text:
        return ""
    
    text = text.strip()
    
    if max_length and len(text) > max_length:
        text = text[:max_length]
    
    return text

def format_phone_number(phone: str) -> str:
    if not phone:
        return ""
    
    digits = re.sub(r'\D', '', phone)
    
    if len(digits) == 11 and digits.startswith('010'):
        return digits
    elif len(digits) == 10 and digits.startswith('10'):
        return '0' + digits
    
    return digits if len(digits) == 11 else "" 