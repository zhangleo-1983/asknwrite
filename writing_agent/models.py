from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class SessionStage(str, Enum):
    TOPIC_ANALYSIS = "审题"
    IDEA = "立意"
    MATERIAL = "选材"
    STRUCTURE = "结构"
    DRAFT = "起草"
    FEEDBACK = "反馈"
    REVIEW = "复盘"


class WritingLevel(str, Enum):
    BEGINNER = "beginner"
    DEVELOPING = "developing"
    PROFICIENT = "proficient"


class GuidancePhase(str, Enum):
    STRONG = "强引导"
    MEDIUM = "半放手"
    LIGHT = "弱引导"
    REVIEW_ONLY = "赛后复盘"


SKILL_LABELS = [
    "审题准确",
    "中心明确",
    "材料具体",
    "顺序清楚",
    "段落完整",
    "细节描写",
    "情感表达",
    "首尾照应",
    "语言通顺",
    "独立完成度",
]


@dataclass
class WritingTask:
    title: str
    age: int
    grade: str
    genre_guess: str = ""
    target_length: int = 500


@dataclass
class StudentProfile:
    level: WritingLevel = WritingLevel.BEGINNER
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=lambda: SKILL_LABELS[:4])
    dependency_score: float = 0.8
    mastered_skills: List[str] = field(default_factory=list)
    completed_sessions: int = 0


@dataclass
class FeedbackItem:
    label: str
    message: str


@dataclass
class SessionState:
    task: WritingTask
    profile: StudentProfile
    stage: SessionStage = SessionStage.TOPIC_ANALYSIS
    collected_materials: List[str] = field(default_factory=list)
    outline: List[str] = field(default_factory=list)
    draft_snippets: List[str] = field(default_factory=list)
    next_best_question: str = ""
    history: List[str] = field(default_factory=list)
    prompt_count: int = 0
    assistance_count: int = 0


@dataclass
class SessionOutput:
    stage: SessionStage
    analysis: str
    questions: List[str] = field(default_factory=list)
    structured_outline: List[str] = field(default_factory=list)
    feedback_items: List[FeedbackItem] = field(default_factory=list)
    practice_task: str = ""
    session_summary: str = ""
    refusal_message: str = ""
