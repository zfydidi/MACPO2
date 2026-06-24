#!/bin/bash
# ============================================================
# MACPO2 自动提交脚本
# 每 12 小时自动 git add/commit/push，附带时间标签
# ============================================================
set -euo pipefail

REPO_DIR="/Users/zhangyingjie/Project/MACPO2"
LOG_FILE="$REPO_DIR/scripts/auto_commit.log"

cd "$REPO_DIR"

# 时间标签
TIMESTAMP=$(date '+%Y-%m-%d_%H:%M:%S')
COMMIT_MSG="auto: 定时备份 $TIMESTAMP"

{
    echo "========== $TIMESTAMP =========="

    # 检查是否有变更
    if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
        echo "无变更，跳过提交"
        exit 0
    fi

    echo "检测到变更，开始提交..."

    # 暂存所有变更（包括未跟踪文件）
    git add -A

    # 提交
    if git commit -m "$COMMIT_MSG"; then
        echo "提交成功: $COMMIT_MSG"
    else
        echo "提交失败或无可提交内容"
        exit 0
    fi

    # 推送到远程（如果有配置 remote）
    REMOTE=$(git remote get-url origin 2>/dev/null || true)
    if [ -n "$REMOTE" ]; then
        echo "推送到 $REMOTE ..."
        git push origin main 2>&1 || echo "推送失败（检查网络或权限）"
    else
        echo "未配置远程仓库，跳过推送"
    fi

    echo "完成"
} >> "$LOG_FILE" 2>&1
