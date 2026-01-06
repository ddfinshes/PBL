"""PBL2.backend.test_agents
对 agents.py 中的节点进行单元测试。
"""
import asyncio
import unittest
from unittest.mock import patch, MagicMock

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.outputs import ChatGeneration

# 在测试环境中，我们需要确保模块可以被正确导入
# 这通常需要配置 PYTHONPATH 或使用相对导入
from . import agents
from .graph import GraphState


class TestAgentNodes(unittest.TestCase):

    def setUp(self):
        """在每个测试用例开始前运行，设置事件循环。"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """在每个测试用例结束后运行，关闭事件循环。"""
        self.loop.close()

    def run_async_test(self, coroutine):
        """一个辅助函数，用于在同步测试方法中运行异步代码。"""
        return self.loop.run_until_complete(coroutine)

    def test_student_analyst_node(self):
        """
        测试 STUDENT_ANALYST 学生节点。
        - 验证它是否能处理输入状态。
        - 验证它是否返回了包含 AIMessage 的正确数据结构。
        - 验证它是否将 next_speaker 设置为 'router'。
        """
        # 1. 准备一个模拟的输入状态
        initial_state = {
            "messages": [HumanMessage(content="这是一个关于胸痛的病例。")],
            "discussion_stage": "初步诊断",
            "summary": "",
            "next_speaker": "",
            "is_teacher_interrupted": False,
        }

        # 2. 创建一个模拟的 AI 回复
        mock_ai_response = AIMessage(content="根据ST段抬高，我首先考虑急性心肌梗死。")
        mock_generation = ChatGeneration(message=mock_ai_response)
        mock_llm_result = MagicMock()
        mock_llm_result.generations = [mock_generation]

        # 3. 使用 patch 来替换真实的 LLM 调用
        with patch('PBL2.backend.agents.STUDENT_LLM') as mock_llm:
            # 配置 mock LLM 的异步方法 agenerate 的返回值
            future = asyncio.Future()
            future.set_result(mock_llm_result)
            mock_llm.agenerate.return_value = future

            # 4. 运行被测试的异步节点函数
            result = self.run_async_test(agents.STUDENT_ANALYST(initial_state))

        # 5. 断言输出是否符合预期
        self.assertIn("messages", result, "输出应包含 'messages' 键")
        self.assertIsInstance(result["messages"], list, "'messages' 应该是一个列表")
        self.assertEqual(len(result["messages"]), 1, "'messages' 列表应包含一个元素")
        
        output_message = result["messages"][0]
        self.assertIsInstance(output_message, AIMessage, "列表中的元素应为 AIMessage")
        self.assertEqual(output_message.content, mock_ai_response.content, "返回的 AI 消息内容不匹配")

        self.assertIn("next_speaker", result, "输出应包含 'next_speaker' 键")
        self.assertEqual(result["next_speaker"], "router", "'next_speaker' 应被设置为 'router'")


# 如何运行测试:
# 在 PBL2 目录下打开终端，然后执行以下命令:
# python -m unittest backend/test_agents.py

if __name__ == '__main__':
    unittest.main()

