from __future__ import annotations

from dataclasses import replace
from typing import List, Tuple

from .models import (
    FeedbackItem,
    GuidancePhase,
    SessionOutput,
    SessionStage,
    SessionState,
    StudentProfile,
    WritingLevel,
    WritingTask,
)


DIRECT_WRITE_SIGNALS = [
    "直接帮我写",
    "帮我写一篇",
    "给我范文",
    "直接出全文",
    "你帮我写完",
]


class WritingCoachAgent:
    def start_session(self, task: WritingTask, profile: StudentProfile) -> Tuple[SessionState, SessionOutput]:
        profile = self._normalize_profile(task, profile)
        state = SessionState(task=task, profile=profile)
        analysis = self._build_topic_analysis(task)
        questions = self._build_questions(state)
        state.next_best_question = questions[0] if questions else ""
        state.prompt_count += len(questions)
        return state, SessionOutput(
            stage=state.stage,
            analysis=analysis,
            questions=questions,
            practice_task=self._build_practice_task(state),
            session_summary="先把题目想清楚，再开始写，效率会更高。",
        )

    def reply(self, state: SessionState, student_reply: str) -> SessionOutput:
        cleaned_reply = student_reply.strip()
        state.history.append(cleaned_reply)

        if self._is_direct_write_request(cleaned_reply):
            state.assistance_count += 1
            return self._build_refusal_output(state)

        if cleaned_reply:
            self._record_student_reply(state, cleaned_reply)

        if self._should_advance(state, cleaned_reply):
            state.stage = self._next_stage(state.stage)

        analysis = self._build_stage_analysis(state, cleaned_reply)
        outline = self._maybe_build_outline(state)
        feedback = self._build_feedback(state, cleaned_reply)
        questions = self._build_questions(state)
        state.next_best_question = questions[0] if questions else ""
        state.prompt_count += len(questions)
        practice_task = self._build_practice_task(state)

        if state.stage == SessionStage.REVIEW:
            state.profile.completed_sessions += 1
            state.profile.dependency_score = self._updated_dependency_score(state)

        return SessionOutput(
            stage=state.stage,
            analysis=analysis,
            questions=questions,
            structured_outline=outline,
            feedback_items=feedback,
            practice_task=practice_task,
            session_summary=self._build_session_summary(state),
        )

    def _normalize_profile(self, task: WritingTask, profile: StudentProfile) -> StudentProfile:
        profile = replace(profile)
        if task.age >= 13 and profile.level == WritingLevel.BEGINNER:
            profile.weaknesses = list(dict.fromkeys(profile.weaknesses + ["首尾照应", "情感表达"]))
        if task.age <= 12 and "立意深化" in profile.weaknesses:
            profile.weaknesses.remove("立意深化")
        return profile

    def _build_topic_analysis(self, task: WritingTask) -> str:
        genre = task.genre_guess or self._guess_genre(task.title)
        focus = self._infer_focus(task.title)
        age_hint = "时间顺序和具体细节" if task.age <= 12 else "中心、转折和情感深化"
        return (
            f"这是一道偏“{genre}”的题目。题目核心是：{focus}。"
            f" 先别急着下笔写完整作文，先把能体现主题的真实材料找出来，重点关注{age_hint}。"
        )

    def _build_stage_analysis(self, state: SessionState, student_reply: str) -> str:
        if state.stage == SessionStage.TOPIC_ANALYSIS:
            return "先确认你写的对象和重点，避免一开始就跑题。"
        if state.stage == SessionStage.IDEA:
            return "现在进入立意阶段，要把“想写什么”缩成一句清楚的话。"
        if state.stage == SessionStage.MATERIAL:
            return "接下来挑材料，只留最能支持中心的 1 到 3 个片段。"
        if state.stage == SessionStage.STRUCTURE:
            return "现在把材料排顺序，形成一个能直接拿来写的结构草图。"
        if state.stage == SessionStage.DRAFT:
            return "开始局部起草。先写最关键的一段，不追求一次写完整篇。"
        if state.stage == SessionStage.FEEDBACK:
            return "先看切题和具体，再看连贯和语言。每次只改最关键的问题。"
        summary = "本轮进入复盘，要把方法记住，而不是只记住这篇作文。"
        if student_reply:
            summary += " 你已经积累了可用素材，下一次可以先自己列提纲。"
        return summary

    def _build_questions(self, state: SessionState) -> List[str]:
        phase = self._guidance_phase(state.profile)
        count = 3 if phase == GuidancePhase.STRONG else 2 if phase == GuidancePhase.MEDIUM else 1

        if state.stage == SessionStage.TOPIC_ANALYSIS:
            questions = self._topic_questions(state.task)
        elif state.stage == SessionStage.IDEA:
            questions = self._idea_questions(state.task)
        elif state.stage == SessionStage.MATERIAL:
            questions = self._material_questions(state.task)
        elif state.stage == SessionStage.STRUCTURE:
            questions = self._structure_questions(state.task, phase)
        elif state.stage == SessionStage.DRAFT:
            questions = self._draft_questions(state.task, phase)
        elif state.stage == SessionStage.FEEDBACK:
            questions = self._feedback_questions()
        else:
            questions = self._review_questions(state.profile)

        return questions[:count]

    def _topic_questions(self, task: WritingTask) -> List[str]:
        if task.age <= 12:
            return [
                "题目里最重要的人、事或景物是谁？先只说一个。",
                "你最想写的那个瞬间发生在什么时候、什么地方？",
                "如果只能告诉老师一件最关键的事，那会是什么？",
            ]
        return [
            "这道题最想让你表达的核心主题是什么？先用一句话说清楚。",
            "题目中哪些词决定了不能跑题？把它们挑出来。",
            "你准备通过哪一件事或哪几个片段来承载这个主题？",
        ]

    def _idea_questions(self, task: WritingTask) -> List[str]:
        if task.age <= 12:
            return [
                "把你想表达的意思先缩成一句简单的话。",
                "你写完这篇后，最想让别人记住你的哪种感受？",
                "这件事里最特别、最不一样的地方是什么？",
            ]
        return [
            "请把中心句压缩成一句完整判断，不要只写情绪词。",
            "这个题目里，你的情感变化或认识变化是什么？",
            "如果删掉一个材料，哪一个不能删？为什么？",
        ]

    def _material_questions(self, task: WritingTask) -> List[str]:
        if task.age <= 12:
            return [
                "把事情按先后顺序说三步：开始、变化、结果。",
                "最关键的那个画面里，你看到了什么、听到了什么？",
                "有没有一个动作、表情或一句话最能说明问题？",
            ]
        return [
            "列出 2 到 3 个最能支撑中心的片段，别把所有事情都写进去。",
            "哪个片段最适合展开细节？它的冲突点或转折点是什么？",
            "有没有一个细节能让读者感到真实，而不是空泛表态？",
        ]

    def _structure_questions(self, task: WritingTask, phase: GuidancePhase) -> List[str]:
        if phase == GuidancePhase.STRONG:
            return [
                "请把结构分成开头、经过、结果三部分，每部分写一句。",
                "哪一段最值得写长一点？为什么？",
                "结尾准备回到题目中的哪个关键词？",
            ]
        return [
            "先独立列一个三段或五段提纲，再告诉我哪一段最关键。",
            "你的结尾会怎样扣回题目，而不是突然结束？",
        ]

    def _draft_questions(self, task: WritingTask, phase: GuidancePhase) -> List[str]:
        if task.age <= 12:
            starter = "先写两三句，交代背景后立刻进入最关键的动作。"
        else:
            starter = "先写最关键的一段，突出转折、感受或认识变化。"

        if phase == GuidancePhase.LIGHT:
            return [starter]
        return [
            starter,
            "写的时候少讲道理，多写看到的、听到的、想到的。",
        ]

    def _feedback_questions(self) -> List[str]:
        return [
            "回头看一遍，你觉得哪一句最像空话？先改它。",
            "哪一段和题目联系最弱？想办法把它拉回中心。",
        ]

    def _review_questions(self, profile: StudentProfile) -> List[str]:
        if self._guidance_phase(profile) == GuidancePhase.REVIEW_ONLY:
            return ["下次先独立列提纲，再把提纲交给我检查是否切题。"]
        return [
            "这次你学会的一个方法是什么？下次准备先自己试哪一步？",
        ]

    def _maybe_build_outline(self, state: SessionState) -> List[str]:
        if state.stage not in {SessionStage.STRUCTURE, SessionStage.DRAFT, SessionStage.FEEDBACK, SessionStage.REVIEW}:
            return state.outline
        if not state.outline:
            state.outline = self._build_outline_from_state(state)
        return state.outline

    def _build_feedback(self, state: SessionState, student_reply: str) -> List[FeedbackItem]:
        items: List[FeedbackItem] = []
        if state.stage not in {SessionStage.DRAFT, SessionStage.FEEDBACK, SessionStage.REVIEW}:
            return items

        if not student_reply:
            return [FeedbackItem(label="先动笔", message="先写一点真实内容，再来改，哪怕只有两三句也可以。")]

        if len(student_reply) < 25:
            items.append(FeedbackItem(label="具体一点", message="内容有点短，再补一个动作、一个画面或一句心里话。"))
        if self._looks_off_topic(state.task.title, student_reply):
            items.append(FeedbackItem(label="拉回题目", message="这段和题目联系还不够紧，试着把题目里的关键词写进句子里。"))
        if self._is_generic(student_reply):
            items.append(FeedbackItem(label="少空话", message="把“我很开心/我很感动”换成具体细节，读者会更容易相信。"))
        if not items:
            items.append(FeedbackItem(label="保持优势", message="这一段已经比较切题，下一步重点加强段与段之间的连接。"))
        return items[:3]

    def _build_practice_task(self, state: SessionState) -> str:
        phase = self._guidance_phase(state.profile)
        if state.stage == SessionStage.TOPIC_ANALYSIS:
            return "先不要写全文，只用 1 句话说清楚你准备写什么。"
        if state.stage == SessionStage.IDEA:
            return "把中心句写出来，要求别人一看就知道你想表达什么。"
        if state.stage == SessionStage.MATERIAL:
            return "列出 1 到 3 个最能支持中心的片段，弱材料先不要。"
        if state.stage == SessionStage.STRUCTURE:
            return "把提纲写成分段笔记，每段只写一句任务说明。"
        if state.stage == SessionStage.DRAFT:
            if phase == GuidancePhase.LIGHT:
                return "独立写出关键段，写完后只让我检查是否切题。"
            return "先写开头或关键段，不求完整，但要有具体细节。"
        if state.stage == SessionStage.FEEDBACK:
            return "按反馈只改 1 到 2 处关键问题，不要一口气全改。"
        return "下次先独立完成提纲，再用它来检验自己是否真的学会了。"

    def _build_session_summary(self, state: SessionState) -> str:
        phase = self._guidance_phase(state.profile)
        if state.stage == SessionStage.REVIEW:
            return (
                f"本次训练重点是{self._focus_skill(state.profile)}。"
                f" 当前引导阶段为“{phase.value}”，下一次会继续减少直接提示。"
            )
        return f"当前在“{state.stage.value}”阶段，先把这一小步做扎实，再进入下一步。"

    def _build_refusal_output(self, state: SessionState) -> SessionOutput:
        outline = state.outline or self._build_outline_from_state(state)
        return SessionOutput(
            stage=state.stage,
            analysis="这次训练的目标是学会写法，不是我替你交作业。",
            structured_outline=outline,
            practice_task="我可以帮你把思路拆成提纲，或者示范一句怎么起笔，但不会直接给整篇成稿。",
            session_summary="先自己写 2 到 3 句，我再帮你看哪里更具体、哪里更切题。",
            refusal_message="已切换回训练模式：只提供提纲、追问和局部示范，不提供整篇代写。",
        )

    def _record_student_reply(self, state: SessionState, student_reply: str) -> None:
        if state.stage in {SessionStage.TOPIC_ANALYSIS, SessionStage.IDEA, SessionStage.MATERIAL}:
            state.collected_materials.append(student_reply)
        elif state.stage in {SessionStage.STRUCTURE, SessionStage.DRAFT}:
            state.draft_snippets.append(student_reply)

        if len(student_reply) < 12:
            state.assistance_count += 1
        elif len(student_reply) > 50:
            state.profile.mastered_skills = list(dict.fromkeys(state.profile.mastered_skills + [self._focus_skill(state.profile)]))

    def _should_advance(self, state: SessionState, student_reply: str) -> bool:
        if state.stage == SessionStage.TOPIC_ANALYSIS:
            return bool(student_reply)
        if state.stage == SessionStage.IDEA:
            return len(student_reply) >= 8
        if state.stage == SessionStage.MATERIAL:
            return len(state.collected_materials) >= 3 or len(student_reply) >= 20
        if state.stage == SessionStage.STRUCTURE:
            return bool(student_reply) or bool(state.outline)
        if state.stage == SessionStage.DRAFT:
            return len(student_reply) >= 15
        if state.stage == SessionStage.FEEDBACK:
            return bool(student_reply)
        return False

    def _next_stage(self, stage: SessionStage) -> SessionStage:
        order = [
            SessionStage.TOPIC_ANALYSIS,
            SessionStage.IDEA,
            SessionStage.MATERIAL,
            SessionStage.STRUCTURE,
            SessionStage.DRAFT,
            SessionStage.FEEDBACK,
            SessionStage.REVIEW,
        ]
        index = order.index(stage)
        return order[min(index + 1, len(order) - 1)]

    def _guidance_phase(self, profile: StudentProfile) -> GuidancePhase:
        if profile.completed_sessions >= 8 and profile.dependency_score <= 0.2:
            return GuidancePhase.REVIEW_ONLY
        if profile.dependency_score >= 0.7:
            return GuidancePhase.STRONG
        if profile.dependency_score >= 0.45:
            return GuidancePhase.MEDIUM
        return GuidancePhase.LIGHT

    def _updated_dependency_score(self, state: SessionState) -> float:
        prompts = max(state.prompt_count, 1)
        raw = state.assistance_count / prompts
        next_score = (state.profile.dependency_score * 0.6) + (raw * 0.4)
        return round(min(max(next_score, 0.0), 1.0), 2)

    def _guess_genre(self, title: str) -> str:
        if any(token in title for token in ["我最", "那一次", "记一次", "难忘"]):
            return "记事"
        if any(token in title for token in ["妈妈", "老师", "同学", "朋友"]):
            return "写人"
        if any(token in title for token in ["春天", "秋天", "校园", "风景"]):
            return "写景"
        if any(token in title for token in ["假如", "如果我", "未来"]):
            return "想象"
        return "命题作文"

    def _infer_focus(self, title: str) -> str:
        title = title.strip()
        if "那一次" in title:
            return "抓住一次关键经历，写清楚前后变化"
        if "我最" in title:
            return "写出你最鲜明的理由，而不是堆很多优点"
        if "如果" in title or "假如" in title:
            return "想象要新，但逻辑要清楚"
        return f"围绕题目“{title}”找到一个最能代表主题的具体切口"

    def _extract_theme(self, state: SessionState) -> str:
        if state.collected_materials:
            return state.collected_materials[0][:18]
        return "真实、具体、切题"

    def _build_outline_from_state(self, state: SessionState) -> List[str]:
        theme = self._extract_theme(state)
        materials = state.collected_materials[:3] or ["交代背景", "展开关键片段", "回扣题目"]
        outline = [
            f"开头：点出题目场景，带出中心“{theme}”。",
            f"中间：重点写“{materials[0]}”，加入动作、语言或心理细节。",
            "结尾：总结感受，再回应题目。",
        ]
        if len(materials) > 1:
            outline.insert(2, f"过渡：补充“{materials[1]}”，让情节更完整。")
        return outline

    def _focus_skill(self, profile: StudentProfile) -> str:
        for weakness in profile.weaknesses:
            if weakness not in profile.mastered_skills:
                return weakness
        return "独立完成度"

    def _is_direct_write_request(self, text: str) -> bool:
        return any(signal in text for signal in DIRECT_WRITE_SIGNALS)

    def _looks_off_topic(self, title: str, text: str) -> bool:
        key_terms = [term for term in title if term.strip()]
        if not key_terms:
            return False
        return not any(term in text for term in key_terms[:4])

    def _is_generic(self, text: str) -> bool:
        generic_phrases = ["我很开心", "我很感动", "我学到了很多", "这让我难忘", "非常有意义"]
        return any(phrase in text for phrase in generic_phrases)
