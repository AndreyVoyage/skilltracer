"""
FSM States for bot handlers.
"""

from aiogram.fsm.state import State, StatesGroup


class DaySelection(StatesGroup):
    selecting_day = State()


class EntryInput(StatesGroup):
    waiting_scores = State()
