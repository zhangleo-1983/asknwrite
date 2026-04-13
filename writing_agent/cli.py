from __future__ import annotations

import json
from dataclasses import asdict

from .engine import WritingCoachAgent
from .models import StudentProfile, WritingLevel, WritingTask


def _print_output(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    print("青少年作文训练 Agent CLI")
    title = input("请输入作文题目: ").strip()
    age = int(input("请输入年龄(9-16): ").strip() or "12")
    grade = input("请输入年级: ").strip() or "六年级"
    level_raw = input("请输入写作水平(beginner/developing/proficient): ").strip() or "beginner"
    dependency_raw = input("请输入依赖度(0-1，默认0.8): ").strip() or "0.8"

    task = WritingTask(title=title, age=age, grade=grade)
    profile = StudentProfile(
        level=WritingLevel(level_raw),
        dependency_score=float(dependency_raw),
    )
    agent = WritingCoachAgent()
    state, opening = agent.start_session(task, profile)
    _print_output(asdict(opening))

    while state.stage.value != "复盘":
        reply = input("\n学生回答: ").strip()
        output = agent.reply(state, reply)
        _print_output(asdict(output))
        if output.stage.value == "复盘":
            break


if __name__ == "__main__":
    main()
