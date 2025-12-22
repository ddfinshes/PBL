from flask import Flask, request, jsonify
from flask_cors import CORS
from config import Config
from services.agent_manager import AgentManager
from services.discussion_service import DiscussionService
from models.agent import AgentProfile
import asyncio

app = Flask(__name__)
CORS(app)

# 初始化服务
agent_manager = AgentManager()
discussion_service = DiscussionService(agent_manager)

def run_async(coro):
    """运行异步函数的辅助函数"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({"status": "ok", "message": "服务运行正常"})

@app.route('/api/agents', methods=['GET'])
def get_agents():
    """获取所有 agent 的配置信息"""
    profiles = agent_manager.get_agent_profiles()
    return jsonify({
        "success": True,
        "agents": profiles
    })

@app.route('/api/agents/<agent_name>', methods=['GET'])
def get_agent(agent_name: str):
    """获取指定 agent 的配置信息"""
    agent = agent_manager.get_agent(agent_name)
    if not agent:
        return jsonify({
            "success": False,
            "message": f"Agent {agent_name} 不存在"
        }), 404
    
    profile = agent.profile
    return jsonify({
        "success": True,
        "agent": {
            "name": profile.name,
            "personality": profile.personality,
            "background": profile.background,
            "expertise": profile.expertise,
            "speaking_style": profile.speaking_style
        }
    })

@app.route('/api/agents/<agent_name>', methods=['PUT'])
def update_agent(agent_name: str):
    """更新 agent 的配置"""
    data = request.json
    
    try:
        profile = AgentProfile(
            name=data.get('name', agent_name),
            personality=data.get('personality', ''),
            background=data.get('background', ''),
            expertise=data.get('expertise', ''),
            speaking_style=data.get('speaking_style', '')
        )
        
        agent_manager.update_agent_profile(agent_name, profile)
        
        return jsonify({
            "success": True,
            "message": f"Agent {agent_name} 配置已更新"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 400

@app.route('/api/discussion/start', methods=['POST'])
def start_discussion():
    """开始新的讨论"""
    data = request.json
    topic = data.get('topic', '')
    max_turns = data.get('max_turns', 10)
    print('-------kkkkk------------------------')
    print(data)
    print('topic: ', topic)
    print('-----------------------------')
    if not topic:
        return jsonify({
            "success": False,
            "message": "讨论主题不能为空"
        }), 400
    try:
        print('--------------------------------messages-2---------------')
        messages = run_async(discussion_service.start_discussion(topic, max_turns))
        
        return jsonify({
            "success": True,
            "topic": topic,
            "messages": messages
        })
    except Exception as e:
        error_msg = str(e)
        print(f"开始讨论错误: {error_msg}")
        # 提供更友好的错误信息
        if "403" in error_msg or "unauthorized" in error_msg.lower() or "forbidden" in error_msg.lower():
            error_msg = "OpenAI API 认证失败，请检查 API Key 是否有效或模型名称是否正确"
        elif "model" in error_msg.lower() or "unsupported" in error_msg.lower():
            error_msg = f"模型配置错误: {error_msg}。请检查 config.py 中的 OPENAI_MODEL 配置（应使用 gpt-4 或 gpt-3.5-turbo）"
        return jsonify({
            "success": False,
            "message": error_msg
        }), 500

@app.route('/api/discussion/agent-response', methods=['POST'])
def get_agent_response():
    """获取指定 agent 的回复"""
    data = request.json
    agent_name = data.get('agent_name', '')
    topic = data.get('topic', '')
    conversation_history = data.get('conversation_history', [])
    
    if not agent_name:
        return jsonify({
            "success": False,
            "message": "Agent 名称不能为空"
        }), 400
    
    try:
        response = run_async(
            discussion_service.add_agent_response(
                agent_name, 
                topic, 
                conversation_history
            )
        )
        
        return jsonify({
            "success": True,
            "response": response
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/discussion/user-message', methods=['POST'])
def add_user_message():
    """添加用户消息"""
    data = request.json
    user_message = data.get('message', '')
    topic = data.get('topic', '')
    conversation_history = data.get('conversation_history', [])
    
    if not user_message:
        return jsonify({
            "success": False,
            "message": "用户消息不能为空"
        }), 400
    
    try:
        updated_history = run_async(
            discussion_service.add_user_message(
                user_message,
                topic,
                conversation_history
            )
        )
        
        return jsonify({
            "success": True,
            "conversation_history": updated_history
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

@app.route('/api/discussion/reset', methods=['POST'])
def reset_discussion():
    """重置讨论"""
    agent_manager.reset_all_conversations()
    return jsonify({
        "success": True,
        "message": "讨论已重置"
    })

if __name__ == '__main__':
    app.run(
        host=Config.API_HOST,
        port=Config.API_PORT,
        debug=Config.FLASK_DEBUG
    )

