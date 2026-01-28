"""이미지 유틸리티 - 크기 최적화"""

import base64
import io
from PIL import Image


def optimize_image(base64_data: str, max_size: int = 1024, quality: int = 85) -> str:
    """
    Base64 이미지를 최적화합니다.
    
    Args:
        base64_data: data:image/... 형식 또는 순수 base64 문자열
        max_size: 최대 가로/세로 픽셀 (기본 1024)
        quality: JPEG 품질 (기본 85)
    
    Returns:
        최적화된 data:image/jpeg;base64,... 형식 문자열
    """
    try:
        # data:image/xxx;base64, 프리픽스 분리
        if base64_data.startswith('data:'):
            header, encoded = base64_data.split(',', 1)
        else:
            encoded = base64_data
        
        # 디코드
        image_bytes = base64.b64decode(encoded)
        image = Image.open(io.BytesIO(image_bytes))
        
        # RGBA -> RGB 변환 (JPEG 저장을 위해)
        if image.mode in ('RGBA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[3] if len(image.split()) == 4 else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # 리사이즈 (비율 유지)
        original_size = max(image.size)
        if original_size > max_size:
            ratio = max_size / original_size
            new_width = int(image.size[0] * ratio)
            new_height = int(image.size[1] * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # JPEG로 저장 (압축)
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=quality, optimize=True)
        optimized_bytes = buffer.getvalue()
        
        # Base64 인코딩
        optimized_base64 = base64.b64encode(optimized_bytes).decode('utf-8')
        
        # 크기 비교 로그
        original_kb = len(encoded) * 3 / 4 / 1024
        optimized_kb = len(optimized_bytes) / 1024
        print(f"[ImageOptimize] {original_kb:.1f}KB -> {optimized_kb:.1f}KB ({(1 - optimized_kb/original_kb)*100:.1f}% 감소)")
        
        return f"data:image/jpeg;base64,{optimized_base64}"
    
    except Exception as e:
        print(f"[ImageOptimize] 최적화 실패: {e}, 원본 반환")
        # 실패 시 원본 반환
        if base64_data.startswith('data:'):
            return base64_data
        return f"data:image/png;base64,{base64_data}"
