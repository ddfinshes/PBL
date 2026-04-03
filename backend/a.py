import json

# Read the file
with open('backend/server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the Chinese types
content = content.replace('{"type": "回答"', '{"type": "Answer"')
content = content.replace('{"type": "点评"', '{"type": "Comment"')

# Replace descriptions (handling the curly quotes)
content = content.replace('"desc": "扮演病人回答，需要提示LLM生成的策略包含"我现在要扮演病人请你回答我""',
                          '"desc": "Act as the patient answering questions. Remind LLM to include \"Now I am acting as the patient, please ask me\" in the strategy."')
content = content.replace('"desc": "one of my favorite questions"',
                          '"desc": "Provide assessment or feedback on student responses"')

# Replace the prompt
old_prompt = '''你是一名资深的医学 PBL 导师（或者是参与 PBL 讨论的标准化病人/家属）。当前讨论背景（最近的消息在最后）如下：'''
new_prompt = '''You are a senior medical PBL teacher (or a standardized patient/family member participating in PBL discussions). The current discussion background (most recent messages at the end) is as follows:'''
content = content.replace(old_prompt, new_prompt)

content = content.replace('请根据当前讨论进度，生成一条建议的教师/导师干预内容。',
                          'Based on the current discussion progress, generate a suggested teacher/mentor intervention.')
content = content.replace('类型：', 'Type: ')
content = content.replace('要求：', 'Requirements:')
content = content.replace(
    '1. 语言专业、亲切，符合医学教育场景。', '1. Professional and warm language that fits the medical education scenario.')
content = content.replace('2. 简明扼要，直接输出干预内容，不要包含任何前缀（如"教师建议内容："）。',
                          '2. Concise and direct output of intervention content. Do not include any prefix (such as "Teacher suggestion:").')
content = content.replace('3. 如果是"回答"类型且当前没有待答复的问题，可以提供一条关于病情的补充信息。',
                          '3. If it\'s the "Answer" type and there are no pending questions to respond to, you can provide supplementary information about the patient\'s condition.')
content = content.replace(
    '4. 确保与上述讨论上下文紧密相关。', '4. Ensure close relevance to the above discussion context.')
content = content.replace(
    '# 注意：ainvoke 是异步的', '# Note: ainvoke is asynchronous')
content = content.replace(
    'f"无法生成该建议：{e}"', 'f"Failed to generate suggestion: {e}"')

# Write the file
with open('server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! File updated.")
