#!/bin/bash

# 停止后端服务脚本

echo "正在查找并停止 Flask 后端服务..."

# 查找运行 app.py 的进程
PIDS=$(ps aux | grep "python.*app.py" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "未找到运行中的后端服务"
else
    for PID in $PIDS; do
        echo "停止进程 $PID"
        kill $PID
    done
    echo "后端服务已停止"
fi

