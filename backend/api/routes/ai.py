"""AI 代理路由
@author ygw
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from ...db import store as db

router = APIRouter()

# ------------------------------------------------------------------ AI 代理
class AiChatBody(BaseModel):
    """AI 分析请求参数"""
    messages: list = Field(...)
    model: str = Field("deepseek-chat")
    temperature: float = Field(0.3)
    max_tokens: int = Field(2000)
    stream: bool = Field(True)


@router.post("/ai/chat")
def ai_chat(body: AiChatBody):
    """
    代理 AI API 调用，避免前端暴露 API Key + CORS 问题。
    流式错误会以 data: {"error":...} 推给前端；超时放宽到 120s（推理模型思考阶段较长）。
    @author ygw
    """
    import httpx
    import json
    import logging
    from fastapi.responses import StreamingResponse, JSONResponse

    logger = logging.getLogger("ai_chat")
    ai_key = db.get_setting("aiApiKey") or db.get_setting("ai_api_key")
    ai_base = db.get_setting("aiBaseUrl") or db.get_setting("ai_base_url") or "https://api.deepseek.com"
    if not ai_key:
        return JSONResponse({"error": {"message": "未配置 AI API Key，请前往设置页配置"}}, status_code=400)

    url = f"{ai_base.rstrip('/')}/v1/chat/completions"
    headers = {"Authorization": f"Bearer {ai_key}", "Content-Type": "application/json"}
    # 推理类模型会先产出 reasoning_content，max_tokens 过小会导致 content 为空
    max_tokens = max(int(body.max_tokens or 2000), 2000)
    payload = {
        "model": body.model,
        "messages": body.messages,
        "temperature": body.temperature,
        "max_tokens": max_tokens,
        "stream": body.stream,
    }
    logger.info("AI 请求 model=%s stream=%s max_tokens=%s base=%s", body.model, body.stream, max_tokens, ai_base)

    if body.stream:
        def generate():
            try:
                with httpx.stream("POST", url, json=payload, headers=headers, timeout=120.0) as resp:
                    if resp.status_code != 200:
                        error_text = resp.read().decode(errors="ignore")
                        logger.warning("AI 上游非200 status=%s body=%s", resp.status_code, error_text[:300])
                        try:
                            err_obj = json.loads(error_text)
                            msg = (err_obj.get("error") or {}).get("message") or error_text
                        except Exception:
                            msg = error_text or f"上游错误 {resp.status_code}"
                        yield f"data: {json.dumps({'error': {'message': msg, 'status': resp.status_code}}, ensure_ascii=False)}\n\n"
                        return
                    for line in resp.iter_lines():
                        if line:
                            yield line + "\n"
                        else:
                            yield "\n"
            except httpx.TimeoutException:
                logger.warning("AI 请求超时 model=%s", body.model)
                yield f"data: {json.dumps({'error': {'message': 'AI 请求超时（推理模型思考较久，可稍后重试或换 deepseek-chat）'}}, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.warning("AI 请求异常 model=%s err=%s", body.model, e)
                yield f"data: {json.dumps({'error': {'message': str(e)}}, ensure_ascii=False)}\n\n"
        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=120.0)
            return JSONResponse(resp.json(), status_code=resp.status_code)
        except Exception as e:
            logger.warning("AI 非流式失败: %s", e)
            return JSONResponse({"error": {"message": str(e)}}, status_code=500)
