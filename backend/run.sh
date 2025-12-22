#!/bin/bash

# 激活 conda 环境
source $(conda info --base)/etc/profile.d/conda.sh
conda activate pbl

# 运行 Flask 应用
python app.py

