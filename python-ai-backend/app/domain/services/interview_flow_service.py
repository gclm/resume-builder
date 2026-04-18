# author: jf
import json
import uuid
from collections.abc import Iterator
from string import hexdigits
from typing import Any

from app.application.ports.agent_runtime_port import AgentRuntimePort
from app.application.ports.llm_port import ChatClientPort
from app.domain.policies.interview_prompt_policy import (
    build_candidate_mode_system_prompt,
    build_interviewer_mode_system_prompt,
)
from app.domain.services.rag_retrieval_service import RagRetrieverService

_ALLOWED_PHASES = {"opening", "skills", "work", "projects", "scenario", "written", "summary"}


class InterviewGraph:
    def __init__(
        self,
        llm_client: ChatClientPort,
        rag_retriever: RagRetrieverService,
        autogen_runtime: AgentRuntimePort,
    ) -> None:
        self.llm_client = llm_client
        self.rag_retriever = rag_retriever
        self.autogen_runtime = autogen_runtime
        self._langgraph_available = False
        self._compiled_graph = self._build_langgraph()

    def _build_langgraph(self) -> Any:
        try:
            from langgraph.graph import END, StateGraph
        except Exception:
            self._langgraph_available = False
            return None

        self._langgraph_available = True
        graph = StateGraph(dict)

        def prepare_node(state: dict[str, Any]) -> dict[str, Any]:
            return self._prepare_state(state)

        def reply_node(state: dict[str, Any]) -> dict[str, Any]:
            model_reply, llm_error = self._safe_chat(state)
            return self._finalize_state(state, model_reply, llm_error=llm_error)

        graph.add_node("prepare", prepare_node)
        graph.add_node("reply", reply_node)
        graph.set_entry_point("prepare")
        graph.add_edge("prepare", "reply")
        graph.add_edge("reply", END)
        return graph.compile()

    def _normalize_mode(self, raw_mode: Any) -> str:
        return "interviewer" if str(raw_mode or "").strip().lower() == "interviewer" else "candidate"

    def _normalize_command(self, raw_command: Any) -> str:
        command = str(raw_command or "").strip().lower()
        if command == "start":
            return "start"
        if command == "finish":
            return "finish"
        return "continue"

    def _build_initial_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        session_id = str(payload.get("sessionId") or "").strip() or str(uuid.uuid4())
        memory_summary = str(payload.get("memorySummary") or "").strip()
        return {
            "sessionId": session_id,
            "mode": self._normalize_mode(payload.get("mode")),
            "command": self._normalize_command(payload.get("command")),
            "userInput": str(payload.get("userInput") or ""),
            "memorySummary": memory_summary,
            "durationMinutes": payload.get("durationMinutes") or 60,
            "elapsedSeconds": payload.get("elapsedSeconds") or 0,
            "history": list(payload.get("history") or []),
            "resumeSnapshot": payload.get("resumeSnapshot") or {},
        }

    def _prepare_state(self, state: dict[str, Any]) -> dict[str, Any]:
        safe_mode = self._normalize_mode(state.get("mode"))
        safe_command = self._normalize_command(state.get("command"))
        question = self._build_retrieval_query(
            command=safe_command,
            mode=safe_mode,
            user_input=str(state.get("userInput") or "").strip(),
        )
        # Align with the Spring implementation: interview turns should be driven
        # directly by recent history, memory summary, and resume snapshot so the
        # first streamed token is not delayed by an extra RAG round trip.
        return {
            **state,
            "mode": safe_mode,
            "command": safe_command,
            "question": question,
            "ragAnswer": "",
            "ragSources": [],
        }

    def prepare_turn(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._prepare_state(self._build_initial_state(payload))

    def stream_turn_reply(self, state: dict[str, Any]) -> Iterator[str]:
        return self.llm_client.stream_chat(
            message=self._build_compact_llm_message(state),
            system_prompt=self._build_system_prompt(state),
        )

    def finalize_stream_turn(
        self,
        state: dict[str, Any],
        raw_text: str,
        *,
        llm_error: str | None = None,
        graph_error: str | None = None,
    ) -> dict[str, Any]:
        return self._to_output(
            self._finalize_state(
                state,
                raw_text,
                llm_error=llm_error,
                graph_error=graph_error,
            )
        )

    def _build_retrieval_query(self, command: str, mode: str, user_input: str) -> str:
        del mode
        if user_input:
            return user_input
        if command == "start":
            return "候选人简历模拟面试开场"
        if command == "finish":
            return "模拟面试总结与改进建议"
        return "继续下一轮中文模拟面试"

    def _default_mode_system_prompt(self, mode: str, resume_snapshot: dict[str, Any]) -> str:
        if mode == "interviewer":
            basic_info = resume_snapshot.get("basicInfo") if isinstance(resume_snapshot, dict) else {}
            job_title = basic_info.get("jobTitle") if isinstance(basic_info, dict) else ""
            return build_interviewer_mode_system_prompt(str(job_title or ""))
        return build_candidate_mode_system_prompt()

    def _build_system_prompt(self, state: dict[str, Any]) -> str:
        mode = self._normalize_mode(state.get("mode"))
        resume_snapshot = state.get("resumeSnapshot") if isinstance(state.get("resumeSnapshot"), dict) else {}
        base_prompt = self._default_mode_system_prompt(mode, resume_snapshot)
        rag_answer = str(state.get("ragAnswer") or "").strip()
        rag_sources = state.get("ragSources")
        if not rag_answer or not isinstance(rag_sources, list) or not rag_sources:
            return base_prompt
        return f"{base_prompt}\n\n补充参考信息（仅在与简历和当前轮次相关时使用，不可编造）：\n{rag_answer}"

    def _build_llm_message(self, state: dict[str, Any]) -> str:
        command = self._normalize_command(state.get("command"))
        command_instruction = {
            "start": "这是面试开始轮次。请根据当前模式生成中文开场，并严格输出 JSON。",
            "continue": "这是面试进行轮次。请结合历史对话、简历与当前输入推进本轮内容，并严格输出 JSON。",
            "finish": "这是面试结束轮次。请输出中文结束语；如果适用请返回 finalEvaluation，并严格输出 JSON。",
        }[command]

        context = {
            "mode": self._normalize_mode(state.get("mode")),
            "command": command,
            "durationMinutes": int(state.get("durationMinutes") or 60),
            "elapsedSeconds": int(state.get("elapsedSeconds") or 0),
            "memorySummary": str(state.get("memorySummary") or "").strip(),
            "userInput": str(state.get("userInput") or "").strip(),
            "history": list(state.get("history") or []),
            "resumeSnapshot": state.get("resumeSnapshot") or {},
            "retrievalQuery": str(state.get("question") or "").strip(),
            "ragContext": str(state.get("ragAnswer") or "").strip(),
        }
        return (
            f"{command_instruction}\n"
            "请严格基于以下上下文完成本轮模拟面试，并且只输出一个 JSON 对象，不要输出 Markdown、代码块或额外解释。\n\n"
            f"{json.dumps(context, ensure_ascii=False, indent=2)}"
        )

    def _truncate_text(self, value: Any, max_len: int) -> str:
        safe_value = str(value or "").strip()
        if len(safe_value) <= max_len:
            return safe_value
        return safe_value[: max(0, max_len - 3)] + "..."

    def _build_history_digest(self, state: dict[str, Any]) -> str:
        history = state.get("history")
        if not isinstance(history, list) or not history:
            return "（无）"

        command = self._normalize_command(state.get("command"))
        window = 4 if command == "start" else 8
        lines: list[str] = []
        for item in history[-window:]:
            if not isinstance(item, dict):
                continue

            role = "assistant" if str(item.get("role") or "").strip().lower() == "assistant" else "user"
            content = self._truncate_text(item.get("content"), 700)
            if not content:
                continue
            lines.append(f"{role}: {content}")

        return "\n".join(lines) if lines else "（无）"

    def _build_resume_digest(self, resume_snapshot: dict[str, Any]) -> str:
        if not isinstance(resume_snapshot, dict) or not resume_snapshot:
            return "空"

        basic_info = resume_snapshot.get("basicInfo")
        safe_basic_info = basic_info if isinstance(basic_info, dict) else {}
        work_list = resume_snapshot.get("workList")
        project_list = resume_snapshot.get("projectList")
        education_list = resume_snapshot.get("educationList")

        lines: list[str] = []
        if safe_basic_info:
            lines.append(
                "基础信息="
                + f"姓名:{self._truncate_text(safe_basic_info.get('name'), 30)},"
                + f"岗位:{self._truncate_text(safe_basic_info.get('jobTitle'), 60)},"
                + f"工作年限:{self._truncate_text(safe_basic_info.get('workYears'), 20)},"
                + f"学历:{self._truncate_text(safe_basic_info.get('educationLevel'), 20)}"
            )

        skills_text = self._truncate_text(resume_snapshot.get("skillsText"), 300)
        if skills_text:
            lines.append(f"技能摘要={skills_text}")

        lines.append(f"工作经历数量={len(work_list) if isinstance(work_list, list) else 0}")
        lines.append(f"项目经历数量={len(project_list) if isinstance(project_list, list) else 0}")
        lines.append(f"教育经历数量={len(education_list) if isinstance(education_list, list) else 0}")

        self_intro = self._truncate_text(resume_snapshot.get("selfIntro"), 300)
        if self_intro:
            lines.append(f"自我介绍={self_intro}")

        return "\n".join(lines) if lines else "空"

    def _build_compact_llm_message(self, state: dict[str, Any]) -> str:
        mode = self._normalize_mode(state.get("mode"))
        command = self._normalize_command(state.get("command"))
        duration_minutes = max(1, int(state.get("durationMinutes") or 60))
        elapsed_seconds = max(0, int(state.get("elapsedSeconds") or 0))
        elapsed_minutes = elapsed_seconds // 60
        remain_minutes = max(duration_minutes - elapsed_minutes, 0)
        user_input = self._truncate_text(state.get("userInput"), 700)
        memory_summary = self._truncate_text(state.get("memorySummary"), 220) or "（无）"
        resume_snapshot = state.get("resumeSnapshot") if isinstance(state.get("resumeSnapshot"), dict) else {}
        rag_answer = self._truncate_text(state.get("ragAnswer"), 500)
        rag_sources = state.get("ragSources")

        if command == "start":
            command_line = (
                "现在开始面试。先请候选人进行 1-2 分钟自我介绍。"
                if mode == "candidate"
                else "现在开始面试。先给出简短开场，然后等待面试官提问。"
            )
        elif command == "finish":
            command_line = "现在结束面试，并给出最终评价。"
        else:
            command_line = f"本轮用户输入：{user_input or '（空）'}"

        sections = [
            f"角色关系：{'你是面试官' if mode == 'candidate' else '你是候选人'}",
            f"目标时长：{duration_minutes} 分钟，已用：{elapsed_minutes} 分钟，剩余：{remain_minutes} 分钟。",
            f"命令：{command}",
            command_line,
            "",
            "最近对话：",
            self._build_history_digest(state),
            "",
            "记忆摘要（优先参考）：",
            memory_summary,
            "",
            "简历快照：",
            self._build_resume_digest(resume_snapshot),
        ]

        if rag_answer and isinstance(rag_sources, list) and rag_sources:
            sections.extend(["", "RAG 参考信息：", rag_answer])

        sections.extend(["", "请仅输出一个 JSON 对象。"])
        return "\n".join(sections)

    def _safe_query_rag(self, query: str, top_k: int) -> tuple[str, list[dict[str, Any]], str | None]:
        try:
            answer, sources = self.rag_retriever.query(query=query, top_k=top_k)
            return str(answer or "").strip(), list(sources or []), None
        except Exception as exc:
            return "", [], f"RAG query failed: {exc}"

    def _safe_chat(self, state: dict[str, Any]) -> tuple[str, str | None]:
        try:
            reply = self.llm_client.chat(
                message=self._build_compact_llm_message(state),
                system_prompt=self._build_system_prompt(state),
            )
            return str(reply or "").strip(), None
        except Exception as exc:
            return "", f"LLM chat failed: {exc}"

    def _extract_json_object(self, raw_text: str) -> dict[str, Any] | None:
        cleaned = (raw_text or "").strip()
        if not cleaned:
            return None

        candidates = [cleaned]
        if cleaned.startswith("```"):
            fenced = cleaned
            if fenced.lower().startswith("```json"):
                fenced = fenced[7:]
            elif fenced.startswith("```"):
                fenced = fenced[3:]
            if fenced.endswith("```"):
                fenced = fenced[:-3]
            fenced = fenced.strip()
            if fenced:
                candidates.insert(0, fenced)

        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if 0 <= first_brace < last_brace:
            candidates.append(cleaned[first_brace : last_brace + 1])

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        return None

    def _extract_assistant_reply_fragment(self, raw_text: str) -> str:
        marker = '"assistantReply"'
        safe_raw = raw_text or ""
        marker_index = safe_raw.find(marker)
        if marker_index < 0:
            return ""

        start_quote = safe_raw.find('"', marker_index + len(marker))
        while start_quote >= 0 and start_quote + 1 < len(safe_raw):
            colon_part = safe_raw[marker_index + len(marker) : start_quote]
            if ":" in colon_part:
                break
            start_quote = safe_raw.find('"', start_quote + 1)
        if start_quote < 0:
            return ""

        idx = start_quote + 1
        chars: list[str] = []
        while idx < len(safe_raw):
            char = safe_raw[idx]
            if char == '"':
                break
            if char != "\\":
                chars.append(char)
                idx += 1
                continue

            idx += 1
            if idx >= len(safe_raw):
                break

            escaped = safe_raw[idx]
            if escaped in {'"', "\\", "/"}:
                chars.append(escaped)
            elif escaped == "b":
                chars.append("\b")
            elif escaped == "f":
                chars.append("\f")
            elif escaped == "n":
                chars.append("\n")
            elif escaped == "r":
                chars.append("\r")
            elif escaped == "t":
                chars.append("\t")
            elif escaped == "u":
                hex_digits_text = safe_raw[idx + 1 : idx + 5]
                if len(hex_digits_text) < 4 or any(item not in hexdigits for item in hex_digits_text):
                    break
                chars.append(chr(int(hex_digits_text, 16)))
                idx += 4
            else:
                chars.append(escaped)
            idx += 1

        return "".join(chars).strip()

    def _normalize_phase(self, raw_phase: Any, default: str) -> str:
        phase = str(raw_phase or "").strip().lower()
        return phase if phase in _ALLOWED_PHASES else default

    def _normalize_next_action(self, raw_next_action: Any, default: str) -> str:
        return "finish" if str(raw_next_action or default).strip().lower() == "finish" else "continue"

    def _normalize_turn_score(self, raw_score: Any) -> dict[str, Any] | None:
        if not isinstance(raw_score, dict):
            return None
        try:
            score = int(raw_score.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        comment = str(raw_score.get("comment") or "").strip()
        if not comment and score == 0:
            return None
        return {"score": max(0, min(100, score)), "comment": comment}

    def _normalize_final_evaluation(self, raw_value: Any) -> dict[str, Any] | None:
        if not isinstance(raw_value, dict):
            return None

        def clamp(value: Any) -> int:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                parsed = 0
            return max(0, min(100, parsed))

        improvements = raw_value.get("improvements")
        normalized_improvements = (
            [str(item).strip() for item in improvements if str(item).strip()]
            if isinstance(improvements, list)
            else []
        )
        summary = str(raw_value.get("summary") or "").strip()
        total_score = clamp(raw_value.get("totalScore"))
        if not summary and total_score == 0 and not normalized_improvements:
            return None
        return {
            "projectScore": clamp(raw_value.get("projectScore")),
            "skillScore": clamp(raw_value.get("skillScore")),
            "workScore": clamp(raw_value.get("workScore")),
            "educationScore": clamp(raw_value.get("educationScore")),
            "totalScore": total_score,
            "passed": bool(raw_value.get("passed")),
            "summary": summary,
            "improvements": normalized_improvements,
        }

    def _fallback_response(self, state: dict[str, Any], raw_text: str | None = None) -> dict[str, Any]:
        memory_summary = str(state.get("memorySummary") or "").strip()
        assistant_reply = str(raw_text or "").strip()
        if not assistant_reply or assistant_reply == "No answer generated by model.":
            assistant_reply = "本轮回答为空，请重试。"

        return {
            "assistantReply": assistant_reply,
            "phase": "opening",
            "nextAction": "continue",
            "turnScore": None,
            "finalEvaluation": None,
            "memorySummary": memory_summary,
        }

    def _parse_model_response(self, raw_text: str, state: dict[str, Any]) -> dict[str, Any]:
        fallback = self._fallback_response(state)
        safe_raw_text = str(raw_text or "").strip()
        if safe_raw_text in {"", "No answer generated by model."}:
            return fallback

        parsed = self._extract_json_object(safe_raw_text)
        if parsed is None:
            assistant_reply_fragment = self._extract_assistant_reply_fragment(safe_raw_text)
            if assistant_reply_fragment:
                return self._fallback_response(state, assistant_reply_fragment)
            return self._fallback_response(state, safe_raw_text)

        assistant_reply = str(parsed.get("assistantReply") or "").strip() or fallback["assistantReply"]
        phase = self._normalize_phase(parsed.get("phase"), str(fallback["phase"]))
        next_action = self._normalize_next_action(parsed.get("nextAction"), str(fallback["nextAction"]))
        turn_score = self._normalize_turn_score(parsed.get("turnScore"))
        final_evaluation = self._normalize_final_evaluation(parsed.get("finalEvaluation"))
        memory_summary = str(parsed.get("memorySummary") or state.get("memorySummary") or "").strip()

        return {
            "assistantReply": assistant_reply,
            "phase": phase,
            "nextAction": next_action,
            "turnScore": turn_score,
            "finalEvaluation": final_evaluation,
            "memorySummary": memory_summary,
        }

    def _decorate_reply(self, assistant_reply: str) -> tuple[str, str | None]:
        try:
            return self.autogen_runtime.decorate_interview_reply(assistant_reply), None
        except Exception as exc:
            return assistant_reply, f"AutoGen decorate failed: {exc}"

    def _finalize_state(
        self,
        state: dict[str, Any],
        raw_text: str,
        *,
        llm_error: str | None = None,
        graph_error: str | None = None,
    ) -> dict[str, Any]:
        next_state = {**state, **self._parse_model_response(raw_text, state)}
        if llm_error:
            next_state["llmError"] = llm_error
        if graph_error:
            next_state["graphError"] = graph_error

        decorated_reply, autogen_error = self._decorate_reply(str(next_state.get("assistantReply") or ""))
        next_state["assistantReply"] = decorated_reply
        if autogen_error:
            next_state["autogenError"] = autogen_error
        return next_state

    def _to_output(self, final_state: dict[str, Any]) -> dict[str, Any]:
        memory_summary = str(final_state.get("memorySummary") or "").strip()
        session_id = str(final_state.get("sessionId") or "").strip() or str(uuid.uuid4())
        return {
            "assistantReply": str(final_state.get("assistantReply") or "").strip(),
            "phase": self._normalize_phase(final_state.get("phase"), "opening"),
            "nextAction": self._normalize_next_action(final_state.get("nextAction"), "continue"),
            "turnScore": self._normalize_turn_score(final_state.get("turnScore")),
            "finalEvaluation": self._normalize_final_evaluation(final_state.get("finalEvaluation")),
            "memorySummary": memory_summary,
            "sessionId": session_id,
            "sources": list(final_state.get("ragSources") or []),
            "meta": {
                "langgraphAvailable": self._langgraph_available,
                "ragError": str(final_state.get("ragError") or "").strip(),
                "llmError": str(final_state.get("llmError") or "").strip(),
                "graphError": str(final_state.get("graphError") or "").strip(),
                "autogenError": str(final_state.get("autogenError") or "").strip(),
            },
        }

    def run_turn(self, payload: dict[str, Any]) -> dict[str, Any]:
        initial_state = self._build_initial_state(payload)

        try:
            if self._compiled_graph is not None:
                final_state = self._compiled_graph.invoke(initial_state)
            else:
                prepared_state = self._prepare_state(initial_state)
                model_reply, llm_error = self._safe_chat(prepared_state)
                final_state = self._finalize_state(prepared_state, model_reply, llm_error=llm_error)
        except Exception as exc:
            prepared_state = self._prepare_state(initial_state)
            final_state = self._finalize_state(
                prepared_state,
                "",
                graph_error=f"Interview graph failed: {exc}",
            )

        return self._to_output(final_state)
