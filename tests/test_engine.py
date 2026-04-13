import unittest

from writing_agent.engine import WritingCoachAgent
from writing_agent.models import SessionStage, StudentProfile, WritingLevel, WritingTask


class WritingCoachAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = WritingCoachAgent()

    def test_start_session_returns_questions_without_full_essay(self) -> None:
        task = WritingTask(title="那一次，我真感动", age=11, grade="五年级")
        profile = StudentProfile(level=WritingLevel.BEGINNER)
        state, output = self.agent.start_session(task, profile)

        self.assertEqual(state.stage, SessionStage.TOPIC_ANALYSIS)
        self.assertTrue(output.questions)
        self.assertNotIn("全文", output.analysis)
        self.assertIn("先不要写全文", output.practice_task)

    def test_direct_write_request_switches_back_to_training_mode(self) -> None:
        task = WritingTask(title="我的老师", age=12, grade="六年级")
        state, _ = self.agent.start_session(task, StudentProfile())
        output = self.agent.reply(state, "直接帮我写一篇满分作文")

        self.assertTrue(output.refusal_message)
        self.assertIn("训练模式", output.refusal_message)
        self.assertTrue(output.structured_outline)

    def test_short_reply_advances_and_generates_specific_questions(self) -> None:
        task = WritingTask(title="难忘的一天", age=10, grade="四年级")
        state, _ = self.agent.start_session(task, StudentProfile())
        output = self.agent.reply(state, "运动会那天我摔倒了")

        self.assertEqual(output.stage, SessionStage.IDEA)
        self.assertGreaterEqual(len(output.questions), 1)
        self.assertIn("一句", output.questions[0])

    def test_older_student_gets_more_abstract_guidance(self) -> None:
        task = WritingTask(title="我读懂了坚持", age=15, grade="初三")
        profile = StudentProfile(level=WritingLevel.DEVELOPING, dependency_score=0.4)
        _, output = self.agent.start_session(task, profile)

        self.assertEqual(len(output.questions), 1)
        self.assertIn("核心主题", output.questions[0])

    def test_draft_feedback_flags_generic_phrases(self) -> None:
        task = WritingTask(title="那一次，我真感动", age=13, grade="初一")
        state, _ = self.agent.start_session(task, StudentProfile(level=WritingLevel.DEVELOPING))
        self.agent.reply(state, "那一次我被同学帮助了")
        self.agent.reply(state, "我想写同学在雨里借我伞，让我明白友情")
        self.agent.reply(state, "先是下雨，然后我没带伞，同学来了")
        self.agent.reply(state, "开头写下雨，中间写借伞，结尾写感谢")
        output = self.agent.reply(state, "我很感动，这让我难忘，也非常有意义。")

        self.assertEqual(output.stage, SessionStage.FEEDBACK)
        self.assertTrue(any(item.label == "少空话" for item in output.feedback_items))

    def test_dependency_score_reduces_after_review(self) -> None:
        task = WritingTask(title="校园里的春天", age=14, grade="初二")
        profile = StudentProfile(level=WritingLevel.PROFICIENT, dependency_score=0.3)
        state, _ = self.agent.start_session(task, profile)

        self.agent.reply(state, "我准备写操场边的树和下课时的风。")
        self.agent.reply(state, "中心是春天让校园重新有了活力。")
        self.agent.reply(state, "先写树发芽，再写操场上的人，最后写我的感受。")
        self.agent.reply(state, "开头点春天，中间写两个画面，结尾扣回校园。")
        self.agent.reply(state, "操场边的树先冒出嫩芽，风一吹，枝条轻轻晃动。")
        output = self.agent.reply(state, "我把空话删掉，补了树叶和笑声。")

        self.assertEqual(output.stage, SessionStage.REVIEW)
        self.assertLessEqual(state.profile.dependency_score, 0.3)


if __name__ == "__main__":
    unittest.main()
