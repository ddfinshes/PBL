from typing import Dict, List, Optional
from models.agent import StudentAgent, AgentProfile
from config import Config

class AgentManager:
    """Agent 管理器"""
    
    def __init__(self):
        self.agents: Dict[str, StudentAgent] = {}
        self.default_profiles = self._create_default_profiles()
        self._initialize_agents()
    
    def _create_default_profiles(self) -> List[AgentProfile]:
        """创建默认的 agent 配置"""
        return [
            AgentProfile(
                name="小明",
                personality="积极乐观，喜欢主动发言，思维活跃",
                background="计算机科学专业，有丰富的编程经验",
                expertise="软件开发和算法设计",
                speaking_style="直接、热情，经常使用技术术语"
            ),
            AgentProfile(
                name="小红",
                personality="细心谨慎，喜欢深入思考，注重细节",
                background="心理学专业，对认知科学感兴趣",
                expertise="用户研究和行为分析",
                speaking_style="温和、有条理，喜欢用例子说明"
            ),
            AgentProfile(
                name="小李",
                personality="理性冷静，善于分析问题，喜欢质疑",
                background="数学专业，逻辑思维强",
                expertise="数据分析和逻辑推理",
                speaking_style="严谨、客观，经常提出反问"
            ),
            AgentProfile(
                name="小张",
                personality="创意丰富，思维跳跃，喜欢创新",
                background="设计专业，有艺术背景",
                expertise="用户体验设计和创新思维",
                speaking_style="生动、富有想象力，经常用比喻"
            )
        ]
    
    def _initialize_agents(self):
        """初始化所有 agents"""
        for profile in self.default_profiles:
            self.agents[profile.name] = StudentAgent(
                profile=profile,
                base_url=Config.OPENAI_BASE_URL,
                api_key=Config.OPENAI_API_KEY,
                model_name=Config.OPENAI_MODEL,
                stream=Config.ENABLE_STREAM
            )
    
    def get_agent(self, name: str) -> Optional[StudentAgent]:
        """获取指定的 agent"""
        return self.agents.get(name)
    
    def get_all_agents(self) -> Dict[str, StudentAgent]:
        """获取所有 agents"""
        return self.agents
    
    def update_agent_profile(self, name: str, profile: AgentProfile):
        """更新 agent 的个人资料"""
        if name in self.agents:
            # 创建新的 agent 实例
            self.agents[name] = StudentAgent(
                profile=profile,
                base_url=Config.OPENAI_BASE_URL,
                api_key=Config.OPENAI_API_KEY,
                model_name=Config.OPENAI_MODEL,
                stream=Config.ENABLE_STREAM
            )
        else:
            # 创建新的 agent
            self.agents[name] = StudentAgent(
                profile=profile,
                base_url=Config.OPENAI_BASE_URL,
                api_key=Config.OPENAI_API_KEY,
                model_name=Config.OPENAI_MODEL,
                stream=Config.ENABLE_STREAM
            )
    
    def reset_all_conversations(self):
        """重置所有 agent 的对话历史"""
        for agent in self.agents.values():
            agent.reset_conversation()
    
    def get_agent_profiles(self) -> List[Dict]:
        """获取所有 agent 的配置信息"""
        return [
            {
                "name": agent.profile.name,
                "personality": agent.profile.personality,
                "background": agent.profile.background,
                "expertise": agent.profile.expertise,
                "speaking_style": agent.profile.speaking_style
            }
            for agent in self.agents.values()
        ]

