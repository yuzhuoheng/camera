import random

# 形容词列表
ADJECTIVES = [
    "可爱的", "奔放的", "快乐的", "聪明的", "勇敢的", "温柔的", "活泼的", 
    "安静的", "神秘的", "优雅的", "调皮的", "真诚的", "友好的", "热情的",
    "机智的", "善良的", "自信的", "坚强的", "自由的", "幸运的", "迷人的",
    "灵巧的", "勤奋的", "乐观的", "酷酷的", "呆萌的"
]

# 动物列表及其对应的头像映射 (这里暂时用占位符，后续可替换为实际 URL)
ANIMALS = {
    "狐狸": "fox",
    "河马": "hippo",
    "熊猫": "panda",
    "兔子": "rabbit",
    "猫咪": "cat",
    "哈士奇": "dog",
    "刺猬": "hedgehog",
    "海豚": "dolphin",
    "猫头鹰": "owl",
    "绵羊": "sheep"
}

def generate_random_nickname() -> str:
    """
    随机生成昵称：形容词 + 动物名
    例如：可爱的狐狸
    """
    adj = random.choice(ADJECTIVES)
    animal = random.choice(list(ANIMALS.keys()))
    return f"{adj}{animal}"

from app.core.config import get_settings

settings = get_settings()

def get_animal_avatar_url(nickname: str) -> str:
    """
    根据昵称中的动物名，返回对应的本地静态头像 URL
    """
    # 尝试从昵称中提取动物名
    found_animal_key = None
    for animal_key in ANIMALS.keys():
        if animal_key in nickname:
            found_animal_key = animal_key
            break
            
    # 构建最终 URL
    # 优先使用 APP_BASE_URL (需包含协议和域名)
    
    domain_prefix = ""
    if settings.APP_BASE_URL:
        domain_prefix = settings.APP_BASE_URL.rstrip("/")
        
    # 拼接完整 URL: https://example.com/cs-server/api/v1/static/avatars/
    base_url = f"{domain_prefix}{settings.API_V1_STR}/static/avatars"

    if found_animal_key:
        animal_filename = f"{ANIMALS[found_animal_key]}.png"
        return f"{base_url}/{animal_filename}"
    
    # 默认头像
    return f"{base_url}/default.png"
