# -*- coding: utf-8 -*-
"""Google NotebookLM — check if notebooklm-py CLI is installed and authenticated."""

import json

from agent_reach.probe import probe_command

from .base import Channel


class NotebookLMChannel(Channel):
    name = "notebooklm"
    description = "Google NotebookLM — AI 研究笔记本"
    backends = ["notebooklm-py CLI"]
    tier = 1

    def can_handle(self, url: str) -> bool:
        from urllib.parse import urlparse
        d = urlparse(url).netloc.lower()
        return "notebooklm.google.com" in d

    def check(self, config=None):
        self.active_backend = None
        findings = []

        for backend in self.ordered_backends(config):
            if backend == "notebooklm-py CLI":
                result = self._check_notebooklm_py()
            else:
                continue
            if result is None:
                continue
            findings.append((backend, *result))

        for wanted in ("ok", "warn"):
            for backend, status, message in findings:
                if status == wanted:
                    self.active_backend = backend
                    return status, message

        if findings:
            return "error", "\n".join(m for _, _, m in findings)

        return "off", (
            "notebooklm-py 未安装。安装方式：\n"
            "  pip install notebooklm-py[browser]\n"
            "然后运行：\n"
            "  notebooklm login"
        )

    def _check_notebooklm_py(self):
        probe = probe_command(
            "notebooklm", ["--version"], timeout=8, retries=0, package="notebooklm-py"
        )
        if probe.status == "missing":
            return None
        if probe.status == "broken":
            return "error", "notebooklm 命令存在但无法执行。\n" + probe.hint
        if probe.status == "timeout":
            return "error", "notebooklm 健康检查超时（已重试 1 次）。\n" + probe.hint

        # Auth check — parse JSON output
        auth_probe = probe_command(
            "notebooklm", ["auth", "check", "--test", "--json"],
            timeout=10, retries=0, package="notebooklm-py"
        )
        if auth_probe.status == "missing":
            return None
        if not auth_probe.ok:
            return "warn", (
                "notebooklm 命令存在但认证检查失败。运行：\n"
                "  notebooklm auth check --test --json\n"
                "查看详细信息。可能需要重新登录：\n"
                "  notebooklm login"
            )

        try:
            data = json.loads(auth_probe.output)
        except (json.JSONDecodeError, ValueError):
            return "warn", "notebooklm 认证检查输出无法解析。"

        status = data.get("status")
        checks = data.get("checks", {})

        if status == "ok" and checks.get("token_fetch"):
            return "ok", (
                "notebooklm-py 已安装且已验证。可用命令：\n"
                "  notebooklm list\n"
                "  notebooklm create \"标题\"\n"
                "  notebooklm source add <url/file>\n"
                "  notebooklm generate audio/report/quiz\n"
                "  notebooklm source fulltext <id>"
            )

        if status == "ok" and not checks.get("token_fetch"):
            return "warn", (
                "notebooklm 配置文件存在但 token 已过期。刷新方式：\n"
                "  notebooklm auth refresh\n"
                "或使用浏览器登录后运行：\n"
                "  notebooklm login --browser-cookies chrome"
            )

        return "warn", (
            "notebooklm 认证未通过。运行以下命令重新登录：\n"
            "  notebooklm login\n"
            "或自动从浏览器提取：\n"
            "  notebooklm login --browser-cookies chrome"
        )
