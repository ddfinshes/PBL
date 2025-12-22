# from gc import callbacks
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
# from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

import os

class AgentProfile(BaseModel):
    """Agent 个人资料"""
    name: str = Field(description="Agent 姓名")
    personality: str = Field(description="性格特征")
    background: str = Field(description="背景信息")
    expertise: str = Field(description="专业领域")
    speaking_style: str = Field(description="说话风格")
    
class StudentAgent:
    """学生 Agent 类"""
    
    def __init__(self, profile: AgentProfile, api_key: str, model_name: str = "qwen3-puls", base_url: str='https://dashscope.aliyuncs.com/compatible-mode/v1', stream: bool = False):
        self.profile = profile
        self.stream_enabled = stream
        
        self.llm = ChatOpenAI(
            model="qwen-plus",  # 您可以按需更换为其它深度思考模型
            openai_api_key=api_key,
            openai_api_base=base_url,
            streaming=False,
            # callbacks=[StreamingStdOutCallbackHandler()],
            # messages=messages,
            extra_body={"enable_thinking": False},
            temperature=0.7,
        )
        self.conversation_history: List = []
        
    def get_system_prompt(self) -> str:
        """生成系统提示词"""
        return f"""你是一个名为 {self.profile.name} 的学生。

个人特征：
- 性格：{self.profile.personality}
- 背景：{self.profile.background}
- 专业领域：{self.profile.expertise}
- 说话风格：{self.profile.speaking_style}

在讨论中，请：
1. 保持你的性格特征和说话风格
2. 基于你的背景和专业领域提供观点
3. 与其他学生进行自然的互动和讨论
4. 可以提出质疑、支持或补充他人的观点
5. 保持对话的自然流畅性

请用中文回复。"""
    
    async def generate_response(self, context: str, other_agents_messages: List[Dict] = None) -> str:
        """生成回复"""
        messages = [SystemMessage(content=self.get_system_prompt())]
        
        # 添加上下文信息
        if context:
            messages.append(HumanMessage(content=f"讨论主题/上下文：{context}"))
        
        # 添加其他 agent 的消息
        if other_agents_messages:
            for msg in other_agents_messages[-5:]:  # 只保留最近5条消息
                if msg['agent'] != self.profile.name:
                    messages.append(HumanMessage(content=f"{msg['agent']}说：{msg['content']}"))
        
        # 添加历史对话
        for hist_msg in self.conversation_history[-3:]:  # 保留最近3条历史
            if isinstance(hist_msg, HumanMessage):
                messages.append(hist_msg)
            elif isinstance(hist_msg, AIMessage):
                messages.append(hist_msg)
        
        # 生成回复
        try:
            # 如果启用了流式输出，需要特殊处理
            if self.stream_enabled:
                # 流式输出：收集所有流式响应的内容
                response_text = ""
                async for chunk in self.llm.astream(messages):
                    if hasattr(chunk, 'content') and chunk.content:
                        response_text += chunk.content
                    elif isinstance(chunk, dict):
                        # 处理字典格式的响应
                        if 'content' in chunk and chunk['content']:
                            response_text += chunk['content']
                        elif 'delta' in chunk and 'content' in chunk['delta']:
                            response_text += chunk['delta']['content']
                    elif isinstance(chunk, str):
                        response_text += chunk
            else:
                # 非流式输出：直接调用
                response = await self.llm.ainvoke(messages)
                if hasattr(response, 'content'):
                    response_text = response.content
                elif isinstance(response, str):
                    response_text = response
                else:
                    response_text = str(response)
            
            if not response_text:
                response_text = "[未收到有效回复]"
            
            # 保存到历史记录
            self.conversation_history.append(AIMessage(content=response_text))
            
            return response_text
        except Exception as e:
            error_msg = f"生成回复时出错: {str(e)}"
            print(f"Agent {self.profile.name} 错误: {error_msg}")
            import traceback
            traceback.print_exc()  # 打印完整错误堆栈
            # 返回错误信息，而不是抛出异常
            return f"[错误：{error_msg}]"
    
    def add_user_message(self, message: str):
        """添加用户消息到历史记录"""
        self.conversation_history.append(HumanMessage(content=f"用户说：{message}"))
    
    def reset_conversation(self):
        """重置对话历史"""
        self.conversation_history = []

