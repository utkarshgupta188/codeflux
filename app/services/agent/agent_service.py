import logging
import json
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.services.agent.tools import TOOLS
from app.services.router import RoutingService

logger = logging.getLogger("agent.service")

class AgentStep(BaseModel):
    step_number: int
    thought: str
    tool: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None
    is_final: bool = False
    answer: Optional[str] = None

class AgentRunResult(BaseModel):
    steps: List[AgentStep]
    final_answer: str

class AgentService:
    @staticmethod
    async def run(prompt: str, repo_id: str = None) -> AgentRunResult:
        """
        Executes the agent loop.
        1. Initialize context with prompt.
        2. Loop (max 10 iterations):
             a. Ask LLM for next step (Thought + Tool or Final Answer).
             b. If Tool: execute tool, append result to context.
             c. If Final Answer: break and return.
        """
        messages = [
            {"role": "system", "content": """You are an autonomous coding agent. 
You have access to a set of tools to explore and analyze a codebase.
Your goal is to answer the user's request by calling tools iteratively.

IMPORTANT PATH RULES:
1. All paths passed to tools MUST be relative to the repository root.
2. DO NOT include virtual prefixes like '/repo/' or '/repo/<id>/'. 
   - WRONG: '/repo/f0565/README.md'
   - RIGHT: 'README.md'
3. Use forward slashes '/' for all paths, even on Windows.
4. If you aren't sure where you are, use 'list_files()' with no arguments to see the root.

Tools available:
- read_file(path, start_line, end_line): Read file content.
- search_code(query, is_regex): Search for string in files.
- list_files(path): List directory contents.
- get_hotspots(limit): Get risky files.

Response Format:
You MUST respond with a JSON object. Do not wrap in markdown blocks.
Format:
{
    "thought": "description of your reasoning",
    "tool": "tool_name", 
    "tool_input": {"arg": "value"},
    "is_final": false
}
OR if you have the answer:
{
    "thought": "I have found the answer",
    "is_final": true,
    "answer": "your markdown formatted answer here"
}
"""},
            {"role": "user", "content": f"Repo ID: {repo_id or 'unknown'}\nRequest: {prompt}"}
        ]

        steps: List[AgentStep] = []
        router = RoutingService()
        
        # Resolve repo_id to physical path
        from app.services.scanner import ScannerService
        root_path = "."
        if repo_id and repo_id in ScannerService.SCANS:
            scan = ScannerService.SCANS[repo_id]
            if scan.rootPath:
                root_path = scan.rootPath
        
        logger.info(f"Agent running for repo {repo_id} at {root_path}")

        for i in range(10): # Safety limit
            # Call LLM
            try:
                # Using 'router' directly might be complex if it expects ChatRequest.
                # Let's bypass for now and assume a direct call or construct a minimal request.
                # Actually router.route_request handles provider selection.
                # We need a simpler interface to just "chat".
                # For MVP, let's use a hardcoded fast model (e.g. Llama-3-70b via Groq) if available, 
                # or reuse the routing logic but forcing JSON mode if possible.
                
                # We'll use a direct call pattern simulating the router's provider call
                # But wait, router.route_request returns ChatResponse. we need the text.

                from app.models.api import ChatRequest
                # Construct the actual prompt for the model from history
                history_text = ""
                for m in messages[1:]:
                   history_text += f"{m['role'].upper()}: {m['content']}\n"

                req = ChatRequest(
                    prompt=history_text,
                    system_prompt=messages[0]["content"],  # Pass the system prompt separately
                    preferred_provider="groq", # Fast inference
                    preferred_model="llama-3.3-70b-versatile" # reliable json
                )

                response = await router.route_request(req)
                content = response["response"]
                
                # Parse JSON
                try:
                    # Cleanup potential markdown ticks
                    content_clean = content.replace("```json", "").replace("```", "").strip()
                    decision = json.loads(content_clean)
                except json.JSONDecodeError:
                    # Retry or fail
                    logger.error(f"Failed to parse agent JSON: {content}")
                    # Feedback to LLM
                    messages.append({"role": "assistant", "content": content})
                    messages.append({"role": "system", "content": "Error: Your response was not valid JSON. Please try again with valid JSON."})
                    continue

                step = AgentStep(
                    step_number=i+1,
                    thought=decision.get("thought", ""),
                    is_final=decision.get("is_final", False),
                    answer=decision.get("answer"),
                    tool=decision.get("tool"),
                    tool_input=decision.get("tool_input")
                )
                steps.append(step)
                
                if step.is_final:
                    return AgentRunResult(steps=steps, final_answer=step.answer)

                # Execute Tool
                tool_name = step.tool
                if tool_name in TOOLS:
                    tool = TOOLS[tool_name]
                    try:
                        kwargs = step.tool_input or {}
                        # Inject context for relevant tools
                        if tool_name in ["read_file", "search_code", "list_files"]:
                           kwargs["root_path"] = root_path
                        if tool_name == "get_hotspots":
                           kwargs["repo_id"] = repo_id
                        
                        result = await tool.run(**kwargs)
                        output = result.error if result.error else result.output
                    except Exception as e:
                        output = f"Tool execution failed: {e}"
                else:
                    output = f"Tool {tool_name} not found."
                
                step.tool_output = output
                
                # Append to history
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "tool", "content": f"Result of {tool_name}: {output}"})

            except Exception as e:
                logger.error(f"Agent loop error: {e}")
                break

        return AgentRunResult(
            steps=steps, 
            final_answer="Agent reached iteration limit or encountered an error."
        )
