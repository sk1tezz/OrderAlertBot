from aiogram.fsm.state import State, StatesGroup


class CreateOrderState(StatesGroup):
    title = State()
    description = State()
    deadline_date = State()
    deadline_time = State()
    confirm = State()
    edit_pick_field = State()
    edit_value = State()


class EditOrderState(StatesGroup):
    pick_field = State()
    value = State()


class NewDeadlineFromOverdueState(StatesGroup):
    value = State()
