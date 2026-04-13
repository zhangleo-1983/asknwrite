# 青少年作文训练 Agent

一个面向 `9-16 岁`学生的中文作文训练原型。它不是代写工具，而是一个按阶段引导学生完成 `审题 -> 立意 -> 选材 -> 结构 -> 起草 -> 反馈 -> 复盘` 的训练型 Agent。

## 当前实现

- 单 Agent + 状态机驱动的训练流程
- `9-12 岁`与`13-16 岁`两套问题风格
- 基于 `dependency_score` 的渐进放手机制
- 防代写约束：遇到“直接帮我写完”会切回训练模式
- 会话输出对象包含：
  - `questions`
  - `structured_outline`
  - `feedback_items`
  - `practice_task`
  - `session_summary`

## 项目结构

```text
writing_agent/
  __init__.py
  cli.py
  engine.py
  models.py
tests/
  test_engine.py
```

## 运行方式

```bash
python3 -m writing_agent.cli
```

## 前端原型

已新增两套粗糙前端 demo：

```bash
open prototype/index.html
open prototype/student.html
```

- `prototype/index.html`：教师 / 观察端工作台
- `prototype/student.html`：学生端聊天界面

如果想用本地静态服务器查看：

```bash
python3 -m http.server 8000
```

然后访问：

- `http://localhost:8000/prototype/index.html`
- `http://localhost:8000/prototype/student.html`

## 运行测试

```bash
python3 -m unittest discover -s tests -v
```

## 设计说明

- 第一版聚焦校内命题作文，不覆盖竞赛作文和成人写作。
- 第一版不接入大模型 API，先把训练状态机、提问策略和反馈逻辑固化成可验证原型。
- 后续如果要接入真实 LLM，可将 `WritingCoachAgent` 作为策略层，把文案生成交给模型，把阶段推进、能力约束和防依赖规则保留在本地逻辑中。
