import logging
from evaluation_config import get_evaluation_config
import uuid
import threading
from datetime import datetime
import json
from flask_cors import CORS
from flask import Flask, request, jsonify
import sys
import io
import os
from pathlib import Path

# Configure stdout and stderr to use UTF-8 encoding for Chinese characters
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ⚠️ IMPORTANT: Load .env file BEFORE importing config
# evaluation_config.py reads os.environ at module load time, so we must populate it first
print(f"[Startup] Loading .env file...")
possible_paths = [
    Path(__file__).parent.parent / '.env',  # 从backend上一级目录
    Path(__file__).parent / '.env',  # backend目录下
    Path.cwd() / '.env',  # 当前工作目录
]

env_loaded = False
for env_path in possible_paths:
    print(f"[Startup] Checking for .env at: {env_path}")
    if env_path.exists():
        print(f"[Startup] ✓ .env file found, loading...")
        try:
            with open(env_path, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip()
                            if key:
                                os.environ[key] = value
                                print(f"[Startup]   → {key}")
            env_loaded = True
            break
        except Exception as e:
            print(f"[Startup] Error reading .env: {e}")
            continue

if not env_loaded:
    print(f"[Startup] ✗ WARNING: .env file not found in any expected location!")

# NOW import evaluation_config after .env is loaded

# 获取配置
config = get_evaluation_config()

# 验证关键配置
print(f"\n[Startup] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(f"[Startup] Configuration Summary (Evaluation):")
print(f"[Startup] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
openai_model = os.environ.get('OPENAI_MODEL')
openai_base_url = os.environ.get('OPENAI_BASE_URL')
openai_api_key = os.environ.get('OPENAI_API_KEY')
print(f"[Startup]   OPENAI_MODEL: {openai_model or '❌ NOT SET'}")
print(f"[Startup]   OPENAI_BASE_URL: {openai_base_url or '❌ NOT SET'}")
print(
    f"[Startup]   OPENAI_API_KEY: {'✓ SET' if openai_api_key else '❌ NOT SET'}")
print(f"[Startup]   CONVERSATIONS_DIR: {config.CONVERSATIONS_DIR}")
print(f"[Startup] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

# 验证必要的配置是否存在
config_errors = []
if not openai_model:
    config_errors.append("OPENAI_MODEL is not set")
if not openai_api_key:
    config_errors.append("OPENAI_API_KEY is not set")
if not openai_base_url:
    config_errors.append("OPENAI_BASE_URL is not set")

if config_errors:
    print(f"[Startup] ❌ CONFIGURATION ERRORS:")
    for error in config_errors:
        print(f"[Startup]    - {error}")
    print(f"[Startup] Please check your .env file at the project root directory.")

# Disable verbose logging for polling requests
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
app.config.from_object(config)
config.init_app(app)

CORS(app, origins=config.CORS_ORIGINS)

# 用户状态管理 - 使用字典存储每个用户的状态，以username为键
user_states = {}
user_states_lock = threading.Lock()

# 全局变量，将在运行时初始化
cases_dir = None
case_files = []

# 简化版本：不再使用case_group和assigned_cases


def get_user_state(username):
    """获取或创建用户状态，使用username作为键"""
    with user_states_lock:
        if username not in user_states:
            user_states[username] = {
                'current_case_index': 0,
                'user_dir': None,
                'case_data': None,
                'initialized': False,
                'user_id': None
            }
            print(f"为用户 {username} 创建新状态")
        else:
            print(
                f"获取用户 {username} 现有状态，当前case_index: {user_states[username]['current_case_index']}")
        return user_states[username]


def initialize_case_files():
    """初始化案例文件列表（从conversations目录）"""
    global cases_dir, case_files
    cases_dir = config.CONVERSATIONS_DIR
    if os.path.exists(cases_dir):
        # 直接从conversations目录获取案例文件夹列表
        all_case_dirs = [d for d in os.listdir(cases_dir)
                         if os.path.isdir(os.path.join(cases_dir, d)) and d.startswith('case')]
        case_files = sorted(all_case_dirs, key=lambda x: int(
            x.replace('case', ''))) if all_case_dirs else []
        print(f"评估系统初始化 - 案例目录: {cases_dir}")
        print(f"从conversations目录获取案例文件夹: {case_files}")
    else:
        print(f"警告：conversations目录不存在: {cases_dir}")
        case_files = []


def load_evaluation_case(case_index, username):
    """加载指定索引的评估案例文件（从conversations目录）"""
    # 确保案例文件已初始化
    if not case_files:
        initialize_case_files()

    # 直接使用全局案例文件列表
    if case_index >= len(case_files):
        print(f"案例索引 {case_index} 超出范围，总案例数: {len(case_files)}")
        return None

    case_folder = os.path.join(cases_dir, case_files[case_index])
    case_file = os.path.join(case_folder, f"{case_files[case_index]}.json")

    print(f"尝试加载案例文件: {case_file}")

    try:
        with open(case_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except Exception:
        return None


def get_next_case_index(username):
    """获取下一个case的索引"""
    if not case_files:
        print(f"案例文件列表为空")
        return 0

    if not os.path.exists(cases_dir):
        print(f"conversations目录不存在: {cases_dir}")
        return 0

    # 简化逻辑：直接返回第一个案例
    print(f"用户 {username} 下一个案例索引: 0 (总案例数: {len(case_files)})")
    return 0


def get_user_dir(username):
    """获取conversations目录（不再为用户创建单独的文件夹）"""
    base_dir = config.CONVERSATIONS_DIR
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        print(f"创建conversations目录: {base_dir}")

    # 直接返回conversations目录，不再为用户创建子目录
    return base_dir


def initialize_case(username):
    """初始化当前案例"""
    user_state = get_user_state(username)

    if user_state['case_data'] is None:
        user_state['case_data'] = load_evaluation_case(
            user_state['current_case_index'], username)

    user_state['initialized'] = True
    print(f"用户 {username} 案例初始化完成，当前索引: {user_state['current_case_index']}")


# Evaluation API 路由

@app.route('/api/evaluation/create-user', methods=['POST'])
def create_evaluation_user():
    """创建评估者用户JSON文件"""
    try:
        data = request.get_json()
        username = data.get('username')

        if not username:
            return jsonify({'error': '用户名不能为空'}), 400

        # 确保evaluators目录存在（在backend目录下）
        evaluators_dir = config.EVALUATORS_DIR
        os.makedirs(evaluators_dir, exist_ok=True)

        user_file = os.path.join(evaluators_dir, f'{username}.json')

        # 检查用户JSON文件是否已存在
        if os.path.exists(user_file):
            # 如果文件已存在，读取现有数据并更新用户信息
            with open(user_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)

            # 更新用户信息，保留其他字段
            existing_data.update({
                'username': username,
                'last_login': datetime.now().isoformat()
            })

            with open(user_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)

            return jsonify({
                'message': '用户已存在，欢迎回来',
                'username': username,
                'is_existing_user': True,
                'current_case_index': existing_data.get('current_case_index', 0),
                'user_file': f'{evaluators_dir}/{username}.json'
            })

        # 如果不存在，则创建用户JSON文件
        user_data = {
            'username': username,
            'created_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat(),
            'evaluations': [],
            'current_case_index': 0,
            'total_cases_completed': 0
        }

        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        return jsonify({
            'message': '用户文件创建成功',
            'username': username,
            'user_file': f'{evaluators_dir}/{username}.json'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/init-user', methods=['POST'])
def init_evaluation_user():
    """根据用户名初始化用户状态"""
    try:
        data = request.json
        username = data.get('username', '')
        user_id = data.get('user_id', str(uuid.uuid4()))

        print(f"[init-user] 收到初始化请求，用户: {username}, user_id: {user_id}")

        if not username:
            print(f"[init-user] 错误：用户名为空")
            return jsonify({'status': 'error', 'message': '用户名不能为空'}), 400

        # 从用户JSON文件中读取现有的 current_case_index
        evaluators_dir = config.EVALUATORS_DIR
        user_file = os.path.join(evaluators_dir, f'{username}.json')
        saved_case_index = 0
        if os.path.exists(user_file):
            try:
                with open(user_file, 'r', encoding='utf-8') as f:
                    user_data = json.load(f)
                    saved_case_index = user_data.get('current_case_index', 0)
                    print(
                        f"[init-user] 从用户文件加载 saved_case_index: {saved_case_index}")
            except Exception as e:
                print(f"[init-user] 读取用户文件失败: {e}")

        user_state = get_user_state(username)
        user_state['user_dir'] = get_user_dir(username)
        user_state['user_id'] = user_id

        # 使用保存的索引，如果没有则使用 get_next_case_index 返回的
        next_case_index = saved_case_index if saved_case_index < len(
            case_files) else get_next_case_index(username)

        # 设置用户状态
        user_state['current_case_index'] = next_case_index
        user_state['case_data'] = load_evaluation_case(
            next_case_index, username)
        initialize_case(username)

        print(
            f"[init-user] 用户 {username} 初始化完成 - case_index: {next_case_index}")

        return jsonify({
            'status': 'success',
            'user_id': user_id,
            'user_dir': user_state['user_dir'],
            'username': username,
            'next_case_index': next_case_index,
            'total_cases': len(case_files),
            'debug_info': {
                'case_files': case_files,
                'current_case_file': case_files[next_case_index] if next_case_index < len(case_files) else 'N/A',
                'loaded_case_index': user_state['current_case_index'],
                'cases_dir': cases_dir
            }
        })
    except Exception as e:
        print(f"[init-user] 初始化失败: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/evaluation/navigate', methods=['POST'])
def navigate_case():
    """处理案例导航（上一个/下一个/直接跳转）"""
    try:
        data = request.json
        # 'next', 'previous' 或 'jump'
        direction = data.get('direction', 'next')
        new_index = data.get('new_index')
        username = data.get('username', '')

        print(
            f"收到导航请求 - 用户: {username}, 方向: {direction}, new_index: {new_index}")

        if not username:
            return jsonify({
                'status': 'error',
                'message': '缺少用户名信息'
            }), 400

        user_state = get_user_state(username)
        current_index = user_state['current_case_index']
        total_cases = len(case_files)

        print(f"用户 {username} 当前case_index: {current_index}, 总案例数: {total_cases}")

        if total_cases == 0:
            return jsonify({
                'status': 'error',
                'message': '没有可用的案例'
            }), 404

        # 根据方向或索引计算新的索引
        if direction == 'jump' and new_index is not None:
            new_index = int(new_index)
            if new_index < 0 or new_index >= total_cases:
                return jsonify({
                    'status': 'error',
                    'message': '索引超出范围'
                }), 400
        elif direction == 'next':
            if current_index >= total_cases - 1:
                return jsonify({
                    'status': 'error',
                    'message': '已经是最后一个案例'
                }), 400
            new_index = current_index + 1
        elif direction == 'previous':
            if current_index <= 0:
                return jsonify({
                    'status': 'error',
                    'message': '已经是第一个案例'
                }), 400
            new_index = current_index - 1
        else:
            return jsonify({
                'status': 'error',
                'message': '无效的导航方向或缺失索引'
            }), 400

        # 更新用户状态
        user_state['current_case_index'] = new_index

        # 持久化当前进度到用户JSON文件
        evaluators_dir = config.EVALUATORS_DIR
        user_file = os.path.join(evaluators_dir, f'{username}.json')
        if os.path.exists(user_file):
            try:
                with open(user_file, 'r', encoding='utf-8') as f:
                    user_data = json.load(f)

                user_data['current_case_index'] = new_index
                user_data['updated_at'] = datetime.now().isoformat()

                with open(user_file, 'w', encoding='utf-8') as f:
                    json.dump(user_data, f, ensure_ascii=False, indent=2)
                print(
                    f"[navigate] 已更新用户 {username} 的 current_case_index 为 {new_index}")
            except Exception as e:
                print(f"[navigate] 更新用户文件失败: {e}")

        # 加载新案例数据
        new_case_data = load_evaluation_case(new_index, username)
        if new_case_data is None:
            return jsonify({
                'status': 'error',
                'message': f'无法加载案例 {new_index + 1} 的数据'
            }), 500

        user_state['case_data'] = new_case_data
        initialize_case(username)

        print(
            f"用户 {username} 从索引 {current_index} 跳转到 {new_index} (方向: {direction})")
        print(
            f"导航后 - 用户 {username} 的 case_data 是否存在: {user_state.get('case_data') is not None}")
        if user_state.get('case_data'):
            print(
                f"导航后 - 案例文件名: {user_state['case_data'].get('case_filename', 'N/A')}")
            print(
                f"导航后 - prompt2 长度: {len(user_state['case_data'].get('prompt2', ''))}")

        case_name = case_files[new_index] if new_index < len(
            case_files) else 'N/A'

        return jsonify({
            'status': 'success',
            'direction': direction,
            'previous_index': current_index,
            'current_index': new_index,
            'total_cases': total_cases,
            'case_name': case_name,
            'message': f'成功跳转到案例 {new_index + 1}'
        })

    except Exception as e:
        import traceback
        print(f"处理导航请求出错: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'处理导航请求失败: {str(e)}'
        }), 500


@app.route('/api/evaluation/current-case', methods=['GET'])
def get_current_evaluation_case():
    """获取当前案例信息"""
    username = request.args.get('username', '')

    if not username:
        return jsonify({
            'status': 'error',
            'message': '缺少用户名信息'
        }), 400

    user_state = get_user_state(username)

    try:
        current_index = user_state['current_case_index']
        case_filename = case_files[current_index] if current_index < len(
            case_files) else "未找到案例"
        total_cases = len(case_files)

        # 创建过滤后的病例数据副本
        filtered_data = {}
        formatted_data = ""  # 初始化formatted_data变量

        if user_state['case_data']:
            # 提取患者基本信息
            if "personal_message" in user_state['case_data']:
                filtered_data["personal_message"] = user_state['case_data']["personal_message"]

            # 提取主诉信息
            if "main_suit" in user_state['case_data']:
                filtered_data["main_suit"] = user_state['case_data']["main_suit"]

            # 格式化为可读字符串
            for key, value in filtered_data.items():
                if key == "personal_message":
                    key_display = "Patient Information"
                elif key == "main_suit":
                    key_display = "Main Suit"
                else:
                    key_display = key.replace("_", " ").title()

                value_display = str(value).replace("\\n", "\n")
                formatted_data += f"{key_display}: {value_display}\n"

        print(f"获取用户 {username} 当前案例信息 - case_index: {current_index}")

        return jsonify({
            'status': 'success',
            'case_index': current_index,
            'case_filename': case_filename,
            'total_cases': total_cases,
            'formatted_data': formatted_data
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取案例信息失败: {str(e)}'
        }), 500


@app.route('/api/evaluation/available-cases', methods=['GET'])
def get_available_cases():
    """获取所有可用的案例列表"""
    try:
        username = request.args.get('username', '')

        # 确保案例文件已初始化
        if not case_files:
            initialize_case_files()

        # 从case文件名中提取case编号 (case1, case2, ...转为 1, 2, ...)
        case_numbers = []
        for case_file in case_files:
            if case_file.startswith('case'):
                try:
                    case_num = int(case_file.replace('case', ''))
                    case_numbers.append(case_num)
                except ValueError:
                    pass

        return jsonify({
            'status': 'success',
            'cases': sorted(case_numbers),
            'total': len(case_numbers)
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取案例列表失败: {str(e)}'
        }), 500


@app.route('/api/evaluation/get-main-suit', methods=['GET'])
def get_evaluation_main_suit():
    """获取当前病例的主诉"""
    username = request.args.get('username', '')

    if not username:
        return jsonify({
            'status': 'error',
            'message': '缺少用户名信息'
        }), 400

    user_state = get_user_state(username)

    try:
        if user_state['case_data'] and 'main_suit' in user_state['case_data']:
            main_suit = user_state['case_data']['main_suit']
            result = {
                'status': 'success',
                'main_suit': main_suit
            }
            return jsonify(result)
        else:
            return jsonify({
                'status': 'error',
                'message': '当前病例没有主诉信息'
            }), 404

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取主诉失败: {str(e)}'
        }), 500


@app.route('/api/evaluation/get-answer', methods=['GET'])
def get_evaluation_answer():
    """获取当前病例的答案"""
    username = request.args.get('username', '')
    force_refresh = request.args.get(
        'force_refresh', 'false').lower() == 'true'

    if not username:
        return jsonify({
            'status': 'error',
            'message': '缺少用户名信息'
        }), 400

    user_state = get_user_state(username)

    # 如果强制刷新，重新加载当前案例数据
    if force_refresh and user_state.get('current_case_index') is not None:
        new_case_data = load_evaluation_case(
            user_state['current_case_index'], username)
        if new_case_data:
            user_state['case_data'] = new_case_data

    try:
        if user_state['case_data']:
            # 获取诊断和治疗方案
            diagnostic = user_state['case_data'].get(
                'Reference_Diagnostic', '')
            treatment = user_state['case_data'].get('Reference_Treatment', '')

            # 获取原始案例内容（不包含prompt1和prompt4）
            original_case = {
                'prompt2': user_state['case_data'].get('prompt2', ''),
                'prompt3': user_state['case_data'].get('prompt3', {})
            }

            result = {
                'status': 'success',
                'diagnostic': diagnostic,
                'treatment': treatment,
                'originalCase': json.dumps(original_case, ensure_ascii=False)
            }
            return jsonify(result)
        else:
            return jsonify({
                'status': 'error',
                'message': '当前病例没有答案信息'
            }), 404

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'获取答案失败: {str(e)}'
        }), 500


@app.route('/api/evaluation/submit', methods=['POST'])
def submit_evaluation():
    """提交评估结果"""
    try:
        data = request.get_json()
        print(f"收到提交请求，数据: {data}")

        username = data.get('username')
        evaluation_results = data.get('evaluation_results', {})

        if not username:
            return jsonify({'error': '缺少用户名信息'}), 400

        # 确保evaluators目录存在
        evaluators_dir = config.EVALUATORS_DIR
        user_file = os.path.join(evaluators_dir, f'{username}.json')

        if not os.path.exists(user_file):
            return jsonify({'error': '用户不存在'}), 404

        # 读取用户文件
        with open(user_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        # 更新用户信息，保留原有信息并添加评估结果
        user_data.update({
            'username': username,
            'evaluation_results': evaluation_results,
            'submitted_at': datetime.now().isoformat()
        })

        # 确保feedback信息被保留，不被覆盖
        if 'feedback' not in user_data:
            user_data['feedback'] = {}

        print(f"准备保存用户数据: {user_data}")

        # 保存更新后的用户文件
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        print(f"用户数据保存成功: {user_file}")

        return jsonify({
            'status': 'success',
            'message': '评估提交成功',
            'username': username
        })

    except Exception as e:
        import traceback
        print(f"提交评估时出错: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/feedback', methods=['POST'])
def save_feedback():
    """保存用户反馈，支持按evaluator_id或agent_name保存"""
    try:
        data = request.get_json()
        print(f"收到反馈保存请求，数据: {data}")

        username = data.get('username')
        case_id = data.get('case_id')
        # 可选的 scene/文件名（例如 trigger_question_scene_2_4）
        scene = data.get('scene') or data.get(
            'scene_filename') or data.get('file')
        evaluator_id = data.get('evaluator_id')  # 向后兼容
        agent_name = data.get('agent_name')      # 新参数：agent名称
        feedback = data.get('feedback', '')

        # 确定使用的标识符：优先使用agent_name，其次使用evaluator_id
        identifier = agent_name or evaluator_id

        if not username or not case_id or not identifier:
            return jsonify({'error': '缺少必要参数'}), 400

        # 确保evaluators目录存在
        evaluators_dir = config.EVALUATORS_DIR
        os.makedirs(evaluators_dir, exist_ok=True)
        user_file = os.path.join(evaluators_dir, f'{username}.json')

        # 如果用户文件不存在，则创建一个新的
        if not os.path.exists(user_file):
            print(f"创建新的用户文件: {user_file}")
            user_data = {
                'username': username,
                'created_at': datetime.now().isoformat(),
                'evaluations': [],
                'current_case_index': 0,
                'total_cases_completed': 0,
                'updated_at': datetime.now().isoformat(),
                'evaluation_results': {},
                'feedback': {}
            }
        else:
            # 读取现有用户文件
            with open(user_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)

        # 初始化feedback结构
        if 'feedback' not in user_data:
            user_data['feedback'] = {}

        case_key = f'case{case_id}'
        if case_key not in user_data['feedback']:
            user_data['feedback'][case_key] = {}

        # 保存反馈
        user_data['feedback'][case_key][identifier] = feedback
        user_data['updated_at'] = datetime.now().isoformat()

        identifier_type = 'agent' if agent_name else 'evaluator'
        print(
            f"准备保存反馈数据 ({identifier_type}:{identifier}): {user_data['feedback']}")

        # 保存更新后的用户文件
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        print(f"反馈数据保存成功: {user_file}")

        return jsonify({
            'status': 'success',
            'message': '反馈保存成功',
            'username': username,
            'case_id': case_id,
            'evaluator_id': evaluator_id
        })

    except Exception as e:
        import traceback
        print(f"保存反馈时出错: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/user/<username>/results', methods=['GET'])
def get_user_evaluation_results(username):
    """获取用户的评估结果"""
    try:
        evaluators_dir = config.EVALUATORS_DIR
        user_file = os.path.join(evaluators_dir, f'{username}.json')

        if not os.path.exists(user_file):
            return jsonify({'error': '用户不存在'}), 404

        # 读取用户文件
        with open(user_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        return jsonify({
            'status': 'success',
            'username': username,
            'user_data': user_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/health', methods=['GET'])
def evaluation_health_check():
    """评估服务健康检查"""
    return jsonify({
        'status': 'healthy',
        'service': 'evaluation',
        'active_users': len(user_states),
        'total_cases': len(case_files),
        'case_files': case_files,
        'cases_dir': cases_dir,
        'conversations_dir': config.CONVERSATIONS_DIR
    })


@app.route('/api/evaluation/case/<int:case_id>/evaluator/<evaluator_id>', methods=['GET'])
def get_evaluator_data(case_id, evaluator_id):
    """获取指定案例和评估者的对话和诊断信息"""
    try:
        # 构建评估者文件路径
        evaluator_file = os.path.join(
            cases_dir, f'case{case_id}', f'{evaluator_id}.json')

        if not os.path.exists(evaluator_file):
            return jsonify({
                'status': 'error',
                'message': f'评估者文件不存在: {evaluator_file}'
            }), 404

        # 读取评估者文件
        with open(evaluator_file, 'r', encoding='utf-8') as f:
            evaluator_data = json.load(f)

        # 提取对话和诊断信息
        conversation = evaluator_data.get('conversation', [])
        diagnosis = evaluator_data.get('Diagnosis', '')
        treatment = evaluator_data.get('Treatment', '')

        return jsonify({
            'status': 'success',
            'conversation': conversation,
            'diagnosis': diagnosis,
            'treatment': treatment
        })

    except Exception as e:
        import traceback
        print(f"获取评估者数据失败: {str(e)}\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'获取评估者数据失败: {str(e)}'
        }), 500


@app.route('/api/evaluation/dimensions', methods=['GET'])
def get_evaluation_dimensions():
    """获取评估维度列表的API端点"""
    try:
        # 读取evaluation_dimensions.json文件
        dimensions_file = os.path.join(os.path.dirname(
            __file__), 'conversations', 'evaluation_dimensions.json')

        if os.path.exists(dimensions_file):
            with open(dimensions_file, 'r', encoding='utf-8') as f:
                dimensions = json.load(f)
            print(f"成功加载评估维度文件: {dimensions_file}")
            print(f"维度数量: {len(dimensions)}")
            return jsonify(dimensions)
        else:
            print(f"评估维度文件不存在: {dimensions_file}")
            # 如果文件不存在，返回默认维度（与evaluation_dimensions.json结构一致）
            default_dimensions = [
                {
                    "dimension": "对话提问是否清晰连贯,前后有逻辑",
                    "anchors": {
                        "1": "毫无逻辑,提问随意",
                        "3": "基本流畅,偶有偏离",
                        "5": "层层推进,符合临床沟通习惯"
                    },
                    "category": "问诊过程逻辑性"
                },
                {
                    "dimension": "最终诊断是否正确",
                    "anchors": {
                        "1": "出现严重误诊,会产生严重不良后果",
                        "3": "诊断虽不准确,但诊断方向与答案一致",
                        "5": "诊断完全正确"
                    },
                    "category": "诊断结论正确性"
                },
                {
                    "dimension": "次要诊断是否全面",
                    "anchors": {
                        "1": "次要诊断错误、遗漏重要次要诊断",
                        "3": "基本涵盖大部分次要诊断但仍有遗漏",
                        "5": "诊断全面"
                    },
                    "category": "诊断结论全面性"
                },
                {
                    "dimension": "诊断推理过程是否合理",
                    "anchors": {
                        "1": "文不对题,诊断理由与诊断不相关",
                        "3": "诊断推理基本合理,但推理链条不完善",
                        "5": "推理充分、证据链完整且能自洽"
                    },
                    "category": "推理过程合理性"
                },
                {
                    "dimension": "治疗建议是否恰当",
                    "anchors": {
                        "1": "治疗方案明显不当,可能对患者产生危害",
                        "3": "治疗方案基本合理,但不够详细,过于宽泛或不符合最佳实践建议",
                        "5": "治疗方案完全合理,符合指南与最佳实践"
                    },
                    "category": "治疗原则合理性"
                },
                {
                    "dimension": "治疗是否全面",
                    "anchors": {
                        "1": "仅给出单一、片面的治疗建议",
                        "3": "覆盖主要治疗措施,但忽视辅助或后续",
                        "5": "治疗全面,既涵盖主要方案,也包括并发症处理、辅助措施和随访计划"
                    },
                    "category": "治疗原则全面性"
                },
                {
                    "dimension": "从患者角度考量,这位医生的诊疗行为是否可被接受",
                    "anchors": {
                        "1": "明显缺乏专业性,回答浅显、不像医生的水准",
                        "3": "有一定专业性,但逻辑或表达仍显不足,更像低年资医生",
                        "5": "高度专业,思路成熟、全面可靠,给人强烈的'深临床医生'感觉"
                    },
                    "category": "临床专业感知"
                },
                {
                    "dimension": "您认为这位'医生'是AI扮演的,还是真实的人类医生?",
                    "anchors": {
                        "0": "非常像 AI,完全不像人类医生",
                        "3": "难以区分,医生和AI的可能性相当",
                        "5": "完全不像AI,非常符合人类医生风格"
                    },
                    "category": "AI感知"
                }
            ]
            return jsonify(default_dimensions)

    except Exception as e:
        print(f"获取评估维度失败: {str(e)}")
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'获取评估维度失败: {str(e)}'
        }), 500


@app.route('/api/evaluation/save-dimension-score', methods=['POST'])
def save_dimension_score():
    """实时保存单个维度的评分，支持按evaluator_id或agent_name保存"""
    try:
        data = request.get_json()
        username = data.get('username')
        case_id = data.get('case_id')
        evaluator_id = data.get('evaluator_id')  # 向后兼容
        agent_name = data.get('agent_name')      # 新参数：agent名称
        dimension_key = data.get('dimension_key')
        score = data.get('score')
        # 可选的 scene/文件名（例如 trigger_question_scene_2_4）
        scene = data.get('scene') or data.get(
            'scene_filename') or data.get('file')

        # 确定使用的标识符：优先使用agent_name，其次使用evaluator_id
        identifier = agent_name or evaluator_id

        if not all([username, case_id, identifier, dimension_key, score is not None]):
            return jsonify({'error': '缺少必要参数'}), 400

        # 确保evaluators目录存在
        evaluators_dir = config.EVALUATORS_DIR
        os.makedirs(evaluators_dir, exist_ok=True)
        user_file = os.path.join(evaluators_dir, f'{username}.json')

        # 如果用户文件不存在，则创建一个新的
        if not os.path.exists(user_file):
            print(f"创建新的用户文件: {user_file}")
            user_data = {
                'username': username,
                'created_at': datetime.now().isoformat(),
                'evaluations': [],
                'current_case_index': 0,
                'total_cases_completed': 0,
                'updated_at': datetime.now().isoformat(),
                'evaluation_results': {},
                'feedback': {}
            }
        else:
            # 读取现有用户文件
            with open(user_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)

        # 初始化数据结构
        if 'evaluation_results' not in user_data:
            user_data['evaluation_results'] = {}

        if case_id not in user_data['evaluation_results']:
            user_data['evaluation_results'][case_id] = {}

        # 如果提供了 scene，则在 case -> scene -> identifier 的结构下保存
        if scene:
            if scene not in user_data['evaluation_results'][case_id]:
                user_data['evaluation_results'][case_id][scene] = {}
            if identifier not in user_data['evaluation_results'][case_id][scene]:
                user_data['evaluation_results'][case_id][scene][identifier] = {
                    'dimensions': {}}

            # 保存评分到 scene 层级
            user_data['evaluation_results'][case_id][scene][identifier]['dimensions'][dimension_key] = score
        else:
            # 向后兼容：case -> identifier 的老结构
            if identifier not in user_data['evaluation_results'][case_id]:
                user_data['evaluation_results'][case_id][identifier] = {
                    'dimensions': {}}
            user_data['evaluation_results'][case_id][identifier]['dimensions'][dimension_key] = score
        user_data['updated_at'] = datetime.now().isoformat()

        # 保存更新后的用户文件
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        identifier_type = 'agent' if agent_name else 'evaluator'
        print(
            f"用户 {username} 的评分已保存: {case_id} - {identifier_type}:{identifier} - {dimension_key} = {score}")

        return jsonify({
            'status': 'success',
            'message': '评分保存成功'
        })

    except Exception as e:
        import traceback
        print(f"保存评分时出错: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/get-user-scores', methods=['GET'])
def get_user_scores():
    """获取用户的所有评分数据"""
    try:
        username = request.args.get('username')
        case_id = request.args.get('case_id')
        # 可选的 scene 查询参数
        scene = request.args.get('scene')

        if not username:
            return jsonify({'error': '缺少用户名信息'}), 400

        # 确保evaluators目录存在
        evaluators_dir = config.EVALUATORS_DIR
        user_file = os.path.join(evaluators_dir, f'{username}.json')

        if not os.path.exists(user_file):
            return jsonify({'error': '用户不存在'}), 404

        # 读取用户文件
        with open(user_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        # 获取评分数据
        evaluation_results = user_data.get('evaluation_results', {})

        print(f"用户 {username} 的评分数据: {evaluation_results}")

        if case_id:
            case_scores = evaluation_results.get(case_id, {})
            # 如果指定了 scene，则只返回该 scene 层级的数据（兼容老数据）
            if scene:
                scene_scores = case_scores.get(scene, {})
                return jsonify({'status': 'success', 'scores': scene_scores})
            # 否则返回整个 case 层级（可能是老结构或包含多个 scene）
            return jsonify({'status': 'success', 'scores': case_scores})
        else:
            # 返回所有case的评分
            return jsonify({
                'status': 'success',
                'scores': evaluation_results
            })

    except Exception as e:
        import traceback
        print(f"获取用户评分时出错: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/initialize-case', methods=['POST'])
def initialize_case_fields():
    """初始化新case的字段"""
    try:
        data = request.get_json()
        username = data.get('username')
        case_id = data.get('case_id')

        if not username or not case_id:
            return jsonify({'error': '缺少用户名或case_id信息'}), 400

        # 确保evaluators目录存在
        evaluators_dir = config.EVALUATORS_DIR
        user_file = os.path.join(evaluators_dir, f'{username}.json')

        if not os.path.exists(user_file):
            return jsonify({'error': '用户不存在'}), 404

        # 读取用户文件
        with open(user_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        # 初始化数据结构
        if 'evaluation_results' not in user_data:
            user_data['evaluation_results'] = {}

        if case_id not in user_data['evaluation_results']:
            user_data['evaluation_results'][case_id] = {}

            # 初始化feedback字段
        if 'feedback' not in user_data:
            user_data['feedback'] = {}

        if case_id not in user_data['feedback']:
            user_data['feedback'][case_id] = {}

        # 更新updated_at时间戳
        user_data['updated_at'] = datetime.now().isoformat()

        # 保存更新后的用户文件
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        print(f"用户 {username} 的case {case_id} 字段初始化成功")

        return jsonify({
            'status': 'success',
            'message': 'case字段初始化成功'
        })

    except Exception as e:
        import traceback
        print(f"初始化case字段时出错: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/save-ranking', methods=['POST'])
def save_ranking():
    """保存用户的排序和档位数据"""
    try:
        data = request.get_json()
        username = data.get('username')
        case_id = data.get('case_id')
        ranking = data.get('ranking', [])
        tiers = data.get('tiers', {})  # 档位数据

        if not username or not case_id:
            return jsonify({'error': '缺少用户名或case_id信息'}), 400

        # 确保evaluators目录存在
        evaluators_dir = config.EVALUATORS_DIR
        user_file = os.path.join(evaluators_dir, f'{username}.json')

        if not os.path.exists(user_file):
            return jsonify({'error': '用户不存在'}), 404

        # 读取用户文件
        with open(user_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        # 初始化数据结构
        if 'evaluation_results' not in user_data:
            user_data['evaluation_results'] = {}

        if case_id not in user_data['evaluation_results']:
            user_data['evaluation_results'][case_id] = {}

        # 保存排序和档位数据
        user_data['evaluation_results'][case_id].update({
            'ranking': ranking,
            'tiers': tiers,
            'saved_at': datetime.now().isoformat()
        })

        # 保存更新后的用户文件
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        print(
            f"用户 {username} 的排序数据已保存: {case_id} - ranking: {ranking}, tiers: {tiers}")

        return jsonify({
            'status': 'success',
            'message': '排序数据保存成功'
        })

    except Exception as e:
        import traceback
        print(f"保存排序数据时出错: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/get-ranking', methods=['GET'])
def get_ranking():
    """获取用户的排序和档位数据"""
    try:
        username = request.args.get('username')
        case_id = request.args.get('case_id')

        if not username:
            return jsonify({'error': '缺少用户名信息'}), 400

        # 确保evaluators目录存在
        evaluators_dir = config.EVALUATORS_DIR
        user_file = os.path.join(evaluators_dir, f'{username}.json')

        if not os.path.exists(user_file):
            return jsonify({'error': '用户不存在'}), 404

        # 读取用户文件
        with open(user_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        # 获取排序数据
        evaluation_results = user_data.get('evaluation_results', {})

        if case_id:
            # 如果指定了case_id，只返回该case的排序数据
            case_data = evaluation_results.get(case_id, {})
            return jsonify({
                'status': 'success',
                'ranking': case_data.get('ranking', []),
                'tiers': case_data.get('tiers', {})
            })
        else:
            # 返回所有case的排序数据
            all_rankings = {}
            for case_key, case_data in evaluation_results.items():
                all_rankings[case_key] = {
                    'ranking': case_data.get('ranking', []),
                    'tiers': case_data.get('tiers', {})
                }
            return jsonify({
                'status': 'success',
                'rankings': all_rankings
            })

    except Exception as e:
        import traceback
        print(f"获取排序数据时出错: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/save-case-state', methods=['POST'])
def save_case_state():
    """保存当前case的排序和打分状态"""
    try:
        data = request.get_json()
        username = data.get('username')
        case_id = data.get('case_id')

        if not username or not case_id:
            return jsonify({'error': '缺少用户名或case_id信息'}), 400

        # 确保evaluators目录存在
        evaluators_dir = config.EVALUATORS_DIR
        user_file = os.path.join(evaluators_dir, f'{username}.json')

        if not os.path.exists(user_file):
            return jsonify({'error': '用户不存在'}), 404

        # 读取用户文件
        with open(user_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

            # 获取当前case的排序数据
        ranking = data.get('ranking', [])

        # 获取评估者评分数据（从data中提取所有评估者数据）
        evaluators_data = {}
        for key, value in data.items():
            if key not in ['username', 'case_id', 'ranking'] and isinstance(value, dict) and 'dimensions' in value:
                evaluators_data[key] = value

        # 更新或创建case的状态
        if 'evaluation_results' not in user_data:
            user_data['evaluation_results'] = {}

        if case_id not in user_data['evaluation_results']:
            user_data['evaluation_results'][case_id] = {}

        # 添加保存状态和评估者数据
        user_data['evaluation_results'][case_id].update({
            'saved': True,
            'saved_at': datetime.now().isoformat(),
            'ranking': ranking
        })

        # 添加每个评估者的数据，合并而不是覆盖
        for evaluator_id, evaluator_data in evaluators_data.items():
            if evaluator_id not in user_data['evaluation_results'][case_id]:
                user_data['evaluation_results'][case_id][evaluator_id] = evaluator_data
            else:
                # 如果评估者已存在，合并dimensions数据
                existing_data = user_data['evaluation_results'][case_id][evaluator_id]
                if 'dimensions' in evaluator_data and 'dimensions' in existing_data:
                    # 合并dimensions，保留已有的评分
                    existing_data['dimensions'].update(
                        evaluator_data['dimensions'])
                else:
                    # 如果结构不匹配，直接替换
                    user_data['evaluation_results'][case_id][evaluator_id] = evaluator_data

        # 保存更新后的用户文件
        with open(user_file, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        print(f"用户 {username} 的case {case_id} 完整状态保存成功")
        print(f"包含 {len(evaluators_data)} 个评估者的评分数据")

        return jsonify({
            'status': 'success',
            'message': 'case状态保存成功',
            'evaluators_count': len(evaluators_data)
        })

    except Exception as e:
        import traceback
        print(f"保存case状态时出错: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/check-submission-eligibility', methods=['GET'])
def check_submission_eligibility():
    """检查用户是否可以提交（是否完成了所有分配的案例）"""
    try:
        username = request.args.get('username')

        if not username:
            return jsonify({'error': '缺少用户名信息'}), 400

        user_state = get_user_state(username)

        # 检查是否完成了所有案例
        total_cases = len(case_files)
        completed_cases = 0
        for case_folder_name in case_files:
            case_folder_path = os.path.join(cases_dir, case_folder_name)
            if os.path.exists(case_folder_path):
                llm_files = [f for f in os.listdir(case_folder_path)
                             if f.startswith('LLM') and f.endswith('.json')]
                if llm_files:
                    completed_cases += 1

        can_submit = completed_cases >= total_cases

        return jsonify({
            'status': 'success',
            'can_submit': can_submit,
            'completed_cases': completed_cases,
            'total_cases': total_cases
        })

    except Exception as e:
        import traceback
        print(f"检查提交资格时出错: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/get-case-state', methods=['GET'])
def get_case_state():
    """获取指定case的保存状态"""
    try:
        username = request.args.get('username')
        case_id = request.args.get('case_id')

        if not username or not case_id:
            return jsonify({'error': '缺少用户名或case_id信息'}), 400

        # 确保evaluators目录存在
        evaluators_dir = config.EVALUATORS_DIR
        user_file = os.path.join(evaluators_dir, f'{username}.json')

        if not os.path.exists(user_file):
            return jsonify({'error': '用户不存在'}), 404

        # 读取用户文件
        with open(user_file, 'r', encoding='utf-8') as f:
            user_data = json.load(f)

        # 获取case状态
        case_state = {
            'saved': False,
            'ranking': None,
            'evaluators': None
        }

        # 检查case是否已经被保存过
        if 'evaluation_results' in user_data:
            case_data = user_data['evaluation_results'].get(case_id, {})

            # 检查是否有saved标记
            if case_data.get('saved', False):
                # 提取评估者数据（排除saved, saved_at, ranking等字段）
                evaluators_data = {}
                for key, value in case_data.items():
                    if key not in ['saved', 'saved_at', 'ranking'] and isinstance(value, dict) and 'dimensions' in value:
                        evaluators_data[key] = value

                case_state.update({
                    'saved': True,
                    'ranking': case_data.get('ranking', None),
                    'evaluators': evaluators_data
                })
            # 检查是否已提交（通过submitted_at字段判断）
            elif 'submitted_at' in user_data:
                # 如果已提交，从提交的数据中提取排序信息
                submitted_case_data = user_data['evaluation_results'].get(
                    case_id, {})
                if 'ranking' in submitted_case_data:
                    # 提取评估者数据
                    evaluators_data = {}
                    for key, value in submitted_case_data.items():
                        if key not in ['saved', 'saved_at', 'ranking'] and isinstance(value, dict) and 'dimensions' in value:
                            evaluators_data[key] = value

                    case_state.update({
                        'saved': True,  # 已提交的case视为已保存
                        'ranking': submitted_case_data.get('ranking', None),
                        'evaluators': evaluators_data
                    })

        return jsonify({
            'status': 'success',
            'case_state': case_state
        })

    except Exception as e:
        import traceback
        print(f"获取case状态时出错: {str(e)}")
        print(f"错误详情: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/evaluation/case/<int:case_id>/evaluators', methods=['GET'])
def get_case_evaluators(case_id):
    """获取指定case的所有evaluator文件列表"""
    try:
        # 找到对应的case文件夹
        case_folder_name = f'case{case_id}'
        case_folder_path = os.path.join(cases_dir, case_folder_name)

        print(
            f"[get_case_evaluators] 正在查找评估者文件，Case: {case_id}, 路径: {case_folder_path}")

        if not os.path.exists(case_folder_path):
            print(f"[get_case_evaluators] Case文件夹不存在: {case_folder_path}")
            return jsonify({'status': 'error', 'message': f'Case {case_id} 不存在'}), 404

        # 获取所有evaluator JSON文件
        evaluators = []
        try:
            files_in_dir = os.listdir(case_folder_path)
            print(f"[get_case_evaluators] 目录中的文件: {files_in_dir}")

            for file in files_in_dir:
                if file.endswith('.json') and file != f'case{case_id}.json':
                    # 这是一个evaluator文件
                    file_path = os.path.join(case_folder_path, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            evaluator_data = json.load(f)
                            evaluator_name = file.replace('.json', '')
                            evaluators.append({
                                'id': evaluator_name,
                                'name': evaluator_name,
                                'file': file,
                                'data': evaluator_data
                            })
                            print(
                                f"[get_case_evaluators] 加载评估者: {evaluator_name}")
                    except Exception as e:
                        print(
                            f"[get_case_evaluators] 加载评估者文件失败: {file}, 错误: {e}")
                        continue
        except Exception as e:
            print(f"[get_case_evaluators] 列举目录失败: {case_folder_path}, 错误: {e}")

        print(
            f"[get_case_evaluators] 成功获取Case {case_id}的评估者数量: {len(evaluators)}")

        return jsonify({
            'status': 'success',
            'case_id': case_id,
            'evaluators': evaluators,
            'total': len(evaluators)
        })

    except Exception as e:
        import traceback
        print(f"[get_case_evaluators] 获取评估者列表时出错: {str(e)}")
        print(f"[get_case_evaluators] 错误详情: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/evaluation/case-agents', methods=['GET'])
def get_case_agents_v2():
    """获取指定 case 中的 agent 配置"""
    try:
        case_id = request.args.get('case_id', 1, type=int)
        print(f"[get_case_agents] 收到请求，Case ID: {case_id}")

        # 确保 case 文件已初始化
        if not case_files:
            initialize_case_files()

        # 查找对应的文件夹名称（例如输入 8，找到 'case8'）
        case_folder_name = f'case{case_id}'

        # 加载 case 文件
        case_file_path = os.path.join(
            config.CONVERSATIONS_DIR, case_folder_name, f"{case_folder_name}.json")

        if not os.path.exists(case_file_path):
            return jsonify({
                'status': 'error',
                'message': f'Case file not found at {case_file_path}'
            }), 404

        with open(case_file_path, "r", encoding="utf-8") as f:
            case_data = json.load(f)

        # 提取 agent/学生信息
        agents = {}
        for key, value in case_data.items():
            if isinstance(value, dict) and 'name' in value:
                agents[key] = value

        print(f"[get_case_agents] 成功加载 {len(agents)} 个 agents")
        return jsonify({
            'status': 'success',
            'case_id': case_id,
            'agents': agents,
            'agent_count': len(agents)
        })

    except Exception as e:
        import traceback
        print(f"[get_case_agents] Error: {str(e)}")
        print(f"[get_case_agents] Traceback: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    # 初始化案例文件
    initialize_case_files()

    # 确保必要的目录存在
    evaluators_dir = config.EVALUATORS_DIR
    os.makedirs(evaluators_dir, exist_ok=True)
    os.makedirs(config.CONVERSATIONS_DIR, exist_ok=True)

    print(f"评估系统启动 - 端口: 5001")
    print(f"案例目录: {config.CONVERSATIONS_DIR}")
    print(f"找到案例文件夹: {case_files}")

    app.run(host='0.0.0.0', debug=config.DEBUG, port=5001)
