"""Telegram bot interface for the interview agent."""
from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command

from src.agent.agent import InterviewAgent
from src.knowledge.retriever import KnowledgeRetriever
from src.llm.base import LLMClient

logger = logging.getLogger(__name__)

router = Router()

# Per-chat agent instances: chat_id -> InterviewAgent
_agents: dict[int, InterviewAgent] = {}

# Shared dependencies (set in run_bot)
_retriever: KnowledgeRetriever | None = None
_llm: LLMClient | None = None
_person_name: str = "Daniel"
_max_chunks: int = 5


def _reset_agent(chat_id: int) -> InterviewAgent:
    """Drop old agent (if any) and create a fresh one."""
    _agents.pop(chat_id, None)
    assert _retriever is not None and _llm is not None
    agent = InterviewAgent(
        llm=_llm,
        retriever=_retriever,
        person_name=_person_name,
        max_chunks=_max_chunks,
    )
    _agents[chat_id] = agent
    return agent


def _get_agent(chat_id: int) -> InterviewAgent:
    """Get existing agent or create a new one."""
    if chat_id not in _agents:
        return _reset_agent(chat_id)
    return _agents[chat_id]


GREETING = (
    "Привет! Это бот-клон Даниила Кравцова, CEO & Co-founder Improvado.\n\n"
    "Что это такое:\n"
    "Бот симулирует первый скрининг-интервью на позицию AI Principal. "
    "Он отвечает как Даниил — сначала узнает про твой опыт, "
    "потом расскажет про компанию и роль, а в конце обсудит тестовое задание. "
    "Вся информация берётся из базы знаний (knowledge base), "
    "в конце каждого ответа видны источники.\n\n"
    "Как пользоваться:\n"
    "— Просто пиши сообщения, как в обычном чате\n"
    "— Бот помнит весь диалог и ведёт интервью поэтапно\n"
    "— /newchat — начать новый диалог с чистого листа "
    "(вся история сбрасывается, как будто интервью только началось)\n\n"
    "Поехали! Расскажи о себе — чем занимаешься, какой у тебя опыт с AI?"
)


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    """Handle /start — first launch, same as newchat."""
    _reset_agent(message.chat.id)
    await message.answer(GREETING.format(name=_person_name))


@router.message(Command("newchat"))
async def cmd_newchat(message: types.Message) -> None:
    """Handle /newchat — wipe memory, start a fresh interview."""
    _reset_agent(message.chat.id)
    await message.answer(
        "Новый диалог! Вся предыдущая история очищена.\n\n"
        "Привет, давай начнём сначала — расскажи о себе!"
    )


@router.message()
async def handle_message(message: types.Message) -> None:
    """Handle text messages — send to agent and reply."""
    if not message.text:
        return

    chat_id = message.chat.id
    agent = _get_agent(chat_id)

    logger.info("Chat %d: %s", chat_id, message.text[:100])
    response = await agent.respond(message.text)
    logger.info("Chat %d: response %d chars", chat_id, len(response))

    # Telegram messages have a 4096 char limit; split if needed
    for i in range(0, len(response), 4096):
        await message.answer(response[i : i + 4096])


async def run_bot(
    token: str,
    retriever: KnowledgeRetriever,
    llm: LLMClient,
    person_name: str = "Daniel",
    max_chunks: int = 5,
) -> None:
    """Start the Telegram bot (blocks until stopped)."""
    global _retriever, _llm, _person_name, _max_chunks  # noqa: PLW0603
    _retriever = retriever
    _llm = llm
    _person_name = person_name
    _max_chunks = max_chunks

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)

    logger.info("Starting Telegram bot...")
    await dp.start_polling(bot)
