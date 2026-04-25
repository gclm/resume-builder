# author: jf
import json
import logging
import uuid
from collections.abc import Iterator
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
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
_LOGGER = logging.getLogger("uvicorn.error")
_RAG_QUERY_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="interview-rag")
_FINAL_EVALUATION_PASS_SCORE = 90
_FINAL_EVALUATION_WEIGHTS = {
    "projectScore": 0.70,
    "skillScore": 0.20,
    "workScore": 0.05,
    "educationScore": 0.05,
}


class InterviewGraph:
    def __init__(
        self,
        llm_client: ChatClientPort,
        rag_retriever: RagRetrieverService,
        autogen_runtime: AgentRuntimePort,
        rag_top_k: int = 5,
        rag_similarity_threshold: float = 0.0,
        rag_timeout_seconds: float = 3.0,
    ) -> None:
        self.llm_client = llm_client
        self.rag_retriever = rag_retriever
        self.autogen_runtime = autogen_runtime
        self.rag_top_k = max(1, int(rag_top_k or 1))
        self.rag_similarity_threshold = self._normalize_similarity_threshold(rag_similarity_threshold)
        self.rag_timeout_seconds = max(0.2, float(rag_timeout_seconds or 3.0))
        # 流式面试链路不依赖 langgraph 编译图，直接走 prepare/stream/finalize。
        # 这里禁用初始化期图编译，避免在构建 InterviewGraph 时被阻塞。
        self._langgraph_available = False
        self._compiled_graph = None

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
        question = self._build_retrieval_query({**state, "mode": safe_mode, "command": safe_command})
        if safe_command == "finish":
            return {
                **state,
                "mode": safe_mode,
                "command": safe_command,
                "question": question,
                "ragAnswer": "",
                "ragSources": [],
                "ragError": "",
            }
        # 面试轮次准备阶段职责：
        # 1) 统一规范 mode/command/query，避免后续链路使用原始脏输入。
        # 2) 在这里完成一次向量检索并把可用上下文放入状态，确保后续 LLM
        #    评估/回答都在同一份检索结果之上，避免回复阶段重复检索造成漂移。
        # 3) 检索失败不抛出到主链路，而是记录 ragError 作为可观察诊断信息。
        rag_answer, rag_sources, rag_error = self._safe_query_rag(query=question, top_k=self.rag_top_k)
        filtered_sources = self._filter_sources_by_similarity(rag_sources)
        rag_answer = self.rag_retriever.build_answer_from_sources(filtered_sources)
        self._log_interview_rag(
            mode=safe_mode,
            command=safe_command,
            query=question,
            rag_sources=rag_sources,
            filtered_sources=filtered_sources,
            rag_answer=rag_answer,
            rag_error=rag_error,
        )

        return {
            **state,
            "mode": safe_mode,
            "command": safe_command,
            "question": question,
            "ragAnswer": rag_answer,
            "ragSources": filtered_sources,
            "ragError": rag_error or "",
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

    def _build_retrieval_query(self, state: dict[str, Any]) -> str:
        command = self._normalize_command(state.get("command"))
        mode = self._normalize_mode(state.get("mode"))
        user_input = self._truncate_text(state.get("userInput"), 240)
        memory_summary = self._truncate_text(state.get("memorySummary"), 160)
        resume_snapshot = state.get("resumeSnapshot") if isinstance(state.get("resumeSnapshot"), dict) else {}
        latest_assistant_focus = self._build_latest_assistant_focus(state)
        resume_keywords = self._build_resume_keyword_digest(resume_snapshot)

        if user_input:
            lead = "检索与当前轮次最相关的项目细节、技术方案、指标结果和追问线索。"
        elif command == "start":
            lead = "检索最适合开场自我介绍和首轮提问的项目亮点、岗位关键词与代表性经历。"
        elif command == "finish":
            lead = "检索模拟面试总结与改进建议。"
        else:
            lead = "检索下一轮模拟面试最相关的上下文。"

        sections = [
            f"模式：{'候选人模式（AI 面试官）' if mode == 'candidate' else '面试官模式（AI 候选人）'}",
            f"命令：{command}",
            f"检索目标：{lead}",
        ]
        if latest_assistant_focus:
            sections.append(f"上一轮 AI 关注点：{latest_assistant_focus}")
        if user_input:
            sections.append(f"当前用户输入：{user_input}")
        if memory_summary:
            sections.append(f"记忆摘要：{memory_summary}")
        if resume_keywords:
            sections.append(f"简历关键词：{resume_keywords}")

        return "\n".join(sections)

    def _build_latest_assistant_focus(self, state: dict[str, Any]) -> str:
        history = state.get("history")
        if not isinstance(history, list):
            return ""
        for item in reversed(history):
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip().lower()
            if role != "assistant":
                continue
            content = self._truncate_text(item.get("content"), 180)
            if content:
                return content
        return ""

    def _build_resume_keyword_digest(self, resume_snapshot: dict[str, Any]) -> str:
        if not isinstance(resume_snapshot, dict) or not resume_snapshot:
            return ""

        basic_info = resume_snapshot.get("basicInfo")
        safe_basic_info = basic_info if isinstance(basic_info, dict) else {}
        work_list = resume_snapshot.get("workList")
        safe_work_list = work_list if isinstance(work_list, list) else []
        project_list = resume_snapshot.get("projectList")
        safe_project_list = project_list if isinstance(project_list, list) else []

        parts: list[str] = []
        job_title = self._truncate_text(safe_basic_info.get("jobTitle"), 50)
        if job_title:
            parts.append(f"岗位:{job_title}")

        skills_text = self._truncate_text(resume_snapshot.get("skillsText"), 160)
        if skills_text:
            parts.append(f"技能:{skills_text}")

        project_keywords: list[str] = []
        for item in safe_project_list[:2]:
            if not isinstance(item, dict):
                continue
            name = self._truncate_text(item.get("name"), 40)
            role = self._truncate_text(item.get("role"), 30)
            main_work = self._truncate_text(item.get("mainWork"), 80)
            project_keywords.append(" / ".join(part for part in [name, role, main_work] if part))
        if project_keywords:
            parts.append(f"项目:{'; '.join(project_keywords)}")

        work_keywords: list[str] = []
        for item in safe_work_list[:2]:
            if not isinstance(item, dict):
                continue
            company = self._truncate_text(item.get("company"), 30)
            position = self._truncate_text(item.get("position"), 30)
            description = self._truncate_text(item.get("description"), 60)
            work_keywords.append(" / ".join(part for part in [company, position, description] if part))
        if work_keywords:
            parts.append(f"工作:{'; '.join(work_keywords)}")

        return "\n".join(parts)

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
        # 这里使用共享线程池承接同步 RAG 查询，避免每次请求都创建临时线程池。
        # 超时时保留首包快速返回，同时把并发线程数量限制在进程级固定上限内。
        future: Future[tuple[str, list[dict[str, Any]]]] = _RAG_QUERY_EXECUTOR.submit(
            self.rag_retriever.query,
            query,
            top_k,
        )
        try:
            answer, sources = future.result(timeout=self.rag_timeout_seconds)
            return str(answer or "").strip(), list(sources or []), None
        except FuturesTimeoutError:
            future.cancel()
            # 超时时不要等待线程自然结束，否则会再次阻塞主链路首包返回。
            future.cancel()
            return "", [], f"RAG query timeout after {self.rag_timeout_seconds:.1f}s"
        except Exception as exc:
            return "", [], f"RAG query failed: {exc}"

    def _normalize_similarity_threshold(self, raw_value: Any) -> float:
        try:
            threshold = float(raw_value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, threshold))

    def _filter_sources_by_similarity(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not isinstance(sources, list):
            return []

        normalized_sources: list[tuple[float, dict[str, Any]]] = []
        for item in sources:
            if not isinstance(item, dict):
                continue

            metadata = item.get("metadata")
            safe_metadata = metadata if isinstance(metadata, dict) else {}
            similarity = safe_metadata.get("similarity")
            try:
                safe_similarity = float(similarity)
            except (TypeError, ValueError):
                safe_similarity = 0.0

            normalized_sources.append((safe_similarity, item))

        if not normalized_sources:
            return []

        normalized_sources.sort(key=lambda pair: pair[0], reverse=True)
        top_similarity = normalized_sources[0][0]
        effective_threshold = self.rag_similarity_threshold
        if effective_threshold <= 0:
            effective_threshold = max(0.18, top_similarity - 0.12)

        filtered: list[dict[str, Any]] = []
        seen_signatures: set[str] = set()
        for index, (safe_similarity, item) in enumerate(normalized_sources):
            if safe_similarity < effective_threshold and not (index == 0 and safe_similarity >= 0.12):
                continue

            source_id = str(item.get("source_id") or "").strip()
            content_signature = self._truncate_text(item.get("content"), 120)
            signature = f"{source_id}:{content_signature}"
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)

            filtered.append(item)
            if len(filtered) >= min(self.rag_top_k, 4):
                break

        return filtered

    def _log_interview_rag(
        self,
        *,
        mode: str,
        command: str,
        query: str,
        rag_sources: list[dict[str, Any]],
        filtered_sources: list[dict[str, Any]],
        rag_answer: str,
        rag_error: str | None,
    ) -> None:
        # 面试检索观测日志：用于本地联调时确认检索命中与阈值过滤效果。
        payload = {
            "mode": mode,
            "command": command,
            "query": query,
            "topK": self.rag_top_k,
            "similarityThreshold": self.rag_similarity_threshold,
            "ragTimeoutSeconds": self.rag_timeout_seconds,
            "ragError": str(rag_error or ""),
            "rawSourceCount": len(rag_sources),
            "filteredSourceCount": len(filtered_sources),
            "rawSources": rag_sources,
            "filteredSources": filtered_sources,
            "ragAnswer": rag_answer,
        }
        _LOGGER.warning("[AI面试][RAG检索] %s", json.dumps(payload, ensure_ascii=False, default=str))

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
        normalized_dimension_scores = {
            "projectScore": clamp(raw_value.get("projectScore")),
            "skillScore": clamp(raw_value.get("skillScore")),
            "workScore": clamp(raw_value.get("workScore")),
            "educationScore": clamp(raw_value.get("educationScore")),
        }
        has_dimension_scores = any(
            raw_value.get(field) is not None for field in _FINAL_EVALUATION_WEIGHTS
        )
        # 结束评分归一职责：
        # 1) 模型负责输出四个维度分和总结，但不再让它自由决定最终总分。
        # 2) 只要分项分存在，就统一按仓库约定权重重算 totalScore，避免前后端展示出的总分漂移。
        # 3) passed 也统一由总分阈值推导，保证“通过 / 未通过”与总分一致。
        weighted_total_score = round(
            sum(normalized_dimension_scores[field] * weight for field, weight in _FINAL_EVALUATION_WEIGHTS.items())
        )
        total_score = weighted_total_score if has_dimension_scores else clamp(raw_value.get("totalScore"))
        if not summary and total_score == 0 and not normalized_improvements:
            return None
        passed = total_score >= _FINAL_EVALUATION_PASS_SCORE
        return {
            **normalized_dimension_scores,
            "totalScore": total_score,
            "passed": passed,
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
