"""
简单的 API 测试脚本
"""
import requests
import json

BASE_URL = "http://localhost:5000/api"

def test_health():
    """测试健康检查"""
    response = requests.get(f"{BASE_URL}/health")
    print("健康检查:", response.json())

def test_get_agents():
    """测试获取所有 agents"""
    response = requests.get(f"{BASE_URL}/agents")
    print("所有 Agents:", json.dumps(response.json(), indent=2, ensure_ascii=False))

def test_start_discussion():
    """测试开始讨论"""
    data = {
        "topic": "如何设计一个用户友好的移动应用界面？",
        "max_turns": 4
    }
    response = requests.post(f"{BASE_URL}/discussion/start", json=data)
    print("讨论结果:", json.dumps(response.json(), indent=2, ensure_ascii=False))

def test_user_message():
    """测试用户消息"""
    data = {
        "message": "我认为应该考虑无障碍设计",
        "topic": "如何设计一个用户友好的移动应用界面？",
        "conversation_history": []
    }
    response = requests.post(f"{BASE_URL}/discussion/user-message", json=data)
    print("用户消息响应:", json.dumps(response.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    print("=" * 50)
    print("开始测试 API")
    print("=" * 50)
    
    try:
        test_health()
        print("\n")
        test_get_agents()
        print("\n")
        # test_start_discussion()  # 需要 API key，取消注释以测试
        # print("\n")
        # test_user_message()
    except requests.exceptions.ConnectionError:
        print("错误: 无法连接到服务器，请确保 Flask 应用正在运行")

