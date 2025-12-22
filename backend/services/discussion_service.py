from typing import Dict, List, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
import random
from services.agent_manager import AgentManager

class DiscussionState(TypedDict):
    """讨论状态"""
    messages: Annotated[List[Dict], "对话消息列表"]
    current_turn: int
    topic: str
    participants: List[str]
    max_turns: int  # 最大轮次

class DiscussionService:
    """讨论服务，使用 LangGraph 管理多 agent 对话"""
    
    def __init__(self, agent_manager: AgentManager):
        self.agent_manager = agent_manager
        self.graph = self._build_graph()
    
    def _build_graph(self):
        """构建 LangGraph 状态图"""
        workflow = StateGraph(DiscussionState)
        
        # 添加节点：每个 agent 的发言节点
        agent_names = list(self.agent_manager.get_all_agents().keys())
        for agent_name in agent_names:
            workflow.add_node(agent_name, self._create_agent_node(agent_name))
        
        # 设置入口点
        workflow.set_entry_point(agent_names[0])
        
        # 添加条件边：决定下一个发言的 agent
        for i, agent_name in enumerate(agent_names):
            next_agent = agent_names[(i + 1) % len(agent_names)]
            workflow.add_edge(agent_name, next_agent)
        
        # 添加结束条件
        workflow.add_conditional_edges(
            agent_names[-1],
            self._should_continue,
            {
                "continue": agent_names[0],
                "end": END
            }
        )
        
        # 编译图，设置递归限制
        return workflow.compile()
    
    def _create_agent_node(self, agent_name: str):
        """创建 agent 节点函数"""
        async def agent_node(state: DiscussionState):
            agent = self.agent_manager.get_agent(agent_name)
            if not agent:
                return {"messages": state["messages"]}
            
            # 获取其他 agent 的消息
            other_messages = [
                msg for msg in state["messages"] 
                if msg.get('agent') != agent_name
            ]
            
            # 生成回复
            response = await agent.generate_response(
                context=state["topic"],
                other_agents_messages=other_messages
            )
            
            # 添加到消息列表
            new_message = {
                "agent": agent_name,
                "content": response,
                "turn": state["current_turn"]
            }
            
            return {
                "messages": state["messages"] + [new_message],
                "current_turn": state["current_turn"] + 1
            }
        
        return agent_node
    
    def _should_continue(self, state: DiscussionState) -> str:
        """判断是否继续讨论"""
        # 检查是否达到最大轮次（留一些余量避免递归限制）
        max_turns = min(20, state.get("max_turns", 20))
        if state["current_turn"] >= max_turns:
            return "end"
        return "continue"
    
    async def start_discussion(self, topic: str, max_turns: int = 10) -> List[Dict]:
        """开始讨论"""
        # 重置所有对话历史
        self.agent_manager.reset_all_conversations()
        
        # 初始化状态
        initial_state: DiscussionState = {
            "topic": topic,
            "participants": list(self.agent_manager.get_all_agents().keys()),
            "current_turn": 0,
            "messages": [],
            "max_turns": max_turns  # 传递最大轮次到状态中
        }
        
        # 运行图，设置递归限制（至少是 max_turns * agent数量 + 余量）
        recursion_limit = max(max_turns * len(initial_state["participants"]) + 10, 50)
        config = {"recursion_limit": recursion_limit}
        
        # 运行图
        final_state = await self.graph.ainvoke(initial_state, config=config)
        
        # 限制轮数
        messages = final_state.get("messages", [])[:max_turns]
        
        return messages
    
    async def add_agent_response(self, agent_name: str, topic: str, conversation_history: List[Dict]) -> Dict:
        """让指定 agent 回复"""
        agent = self.agent_manager.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent {agent_name} not found")
        
        response = await agent.generate_response(
            context=topic,
            other_agents_messages=conversation_history
        )
        
        return {
            "agent": agent_name,
            "content": response,
            "turn": len(conversation_history)
        }
    
    async def add_user_message(self, user_message: str, topic: str, conversation_history: List[Dict]) -> List[Dict]:
        """添加用户消息，并让所有 agent 响应"""
        # 添加用户消息到历史
        user_msg = {
            "agent": "用户",
            "content": user_message,
            "turn": len(conversation_history)
        }
        updated_history = conversation_history + [user_msg]
        
        # 让所有 agent 知道用户的消息
        for agent in self.agent_manager.get_all_agents().values():
            agent.add_user_message(user_message)
        
        return updated_history

