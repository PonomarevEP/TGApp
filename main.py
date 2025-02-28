import random
import tokens

from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

import sqlalchemy
import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.inspection import inspect

Base = declarative_base()

class TGUsers(Base):
    __tablename__ = "tg_users"
    
    id = sq.Column(sq.Integer, primary_key=True)
    tg_user_id = sq.Column(sq.Integer, nullable=False)
    user_name = sq.Column(sq.String(length=40))

class Words(Base):
    __tablename__ = "words"
    
    id = sq.Column(sq.Integer, primary_key=True)
    id_users = sq.Column(sq.Integer, sq.ForeignKey('tg_users.id'))
    engword = sq.Column(sq.String(length=40))
    ruword = sq.Column(sq.String(length=40))

class UserStep(Base):
    __tablename__ = "user_Step"
    
    id = sq.Column(sq.Integer, primary_key=True)
    id_users = sq.Column(sq.Integer, nullable=False)
    step = sq.Column(sq.Integer)

engine = sqlalchemy.create_engine(tokens.connection_string)

def user_request(engine):
    session = sessionmaker(bind=engine)
    session = session()
    
    result = session.query(TGUsers).all()
    result_list = []
    for i in result:
        result_list.append(i.tg_user_id)
    return result_list

def load_user_steps(engine):
    session = sessionmaker(bind=engine)()
    results = session.query(UserStep).all()
    if not results:
        return {}
    else:
        userStep = {row.id_users: row.step for row in results}
    return userStep

insp = inspect(engine)
exists = insp.has_table('tg_users')
if not exists:
    Base.metadata.create_all(engine)

    session = sessionmaker(bind=engine)
    session = session()

    user = TGUsers(tg_user_id=1, user_name='user1')
    session.add(user)
    session.commit()

    word1 = Words(id_users=1, engword='hello', ruword='привет')
    word2 = Words(id_users=1, engword='good', ruword='хорошо')
    word3 = Words(id_users=1, engword='evening', ruword='вечер')
    word4 = Words(id_users=1, engword='thank', ruword='спасибо')
    word5 = Words(id_users=1, engword='welcome', ruword='добро пожаловать')
    word6 = Words(id_users=1, engword='yes', ruword='да')
    word7 = Words(id_users=1, engword='no', ruword='нет')
    word8 = Words(id_users=1, engword='please', ruword='пожалуйста')
    word9 = Words(id_users=1, engword='sorry', ruword='извините')
    word10 = Words(id_users=1, engword='speak', ruword='говорить')
    word11 = Words(id_users=1, engword='little', ruword='мало')
    word12 = Words(id_users=1, engword='help', ruword='помочь')

    session.add_all([word1, word2, word3, word4, word5, word6, word7, word8, word9, word10, word11, word12])
    session.commit()

# Запуск бота
print('Start telegram bot...')

state_storage = StateMemoryStorage()
token_bot = tokens.access_token
bot = TeleBot(token_bot, state_storage=state_storage)
known_users = user_request(engine) 
userStep = load_user_steps(engine)
buttons = []


def show_hint(*lines):
    return '\n'.join(lines)


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()
    new_eng_word = State()
    new_ru_word = State()


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        session = sessionmaker(bind=engine)
        session = session()
        new_user_step = UserStep(id_users=uid, step=0)
        session.add(new_user_step)
        session.commit()
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


@bot.message_handler(commands=['cards', 'start'])
def create_cards(message):
    cid = message.chat.id
    if cid not in known_users:
        known_users.append(cid)
        
        session = sessionmaker(bind=engine)
        session = session()
        usr = TGUsers(tg_user_id=cid, user_name=message.from_user.username)
        session.add(usr)
        session.commit()
        
        userStep[cid] = 0
        new_user_step = UserStep(id_users=cid, step=0)
        session.add(new_user_step)
        session.commit()
        bot.send_message(cid, "Hello, stranger, let study English...")
    markup = types.ReplyKeyboardMarkup(row_width=2)
    
    current_step = get_user_step(cid)
    session = sessionmaker(bind=engine)
    session = session()
    new_user_step = UserStep(id_users=cid, step=current_step + 1)
    session.add(new_user_step)
    session.commit()
    userStep[cid] = current_step + 1
    
    words = []
    id = session.query(TGUsers).filter(TGUsers.tg_user_id == cid).first().id
    сommon_words = session.query(Words).filter(Words.id_users == 1).all()
    for word in сommon_words:
        words.append([word.engword, word.ruword])
    user_words = session.query(Words).filter(Words.id_users == id).all()
    for word in user_words:
        words.append([word.engword, word.ruword])
    
    global buttons
    buttons.clear()
    buttons = []
    target_word, translate = random.choice(words)
    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)

    others = random.sample(words, k=3)

    other_words_btns = [types.KeyboardButton(word[0]) for word in others if word[0] != target_word]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        
        session = sessionmaker(bind=engine)()
        
        current_user = session.query(TGUsers).filter(TGUsers.tg_user_id == message.chat.id).one_or_none()
        if not current_user:
            bot.send_message(message.chat.id, "Ошибка: Пользователь не найден.")
            return
        
        deleted = session.query(Words).filter(
            Words.engword == target_word,
            Words.id_users == current_user.id
        ).delete()
        
        session.commit()
        
        if deleted > 0:
            bot.send_message(message.chat.id, f"Слово '{target_word}' успешно удалено.")
        else:
            bot.send_message(message.chat.id, f"Слово '{target_word}' не найдено.")


@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word(message):

    cid = message.chat.id
    bot.send_message(cid, "Введите английское слово:")
    bot.set_state(message.from_user.id, MyStates.new_eng_word, message.chat.id)

@bot.message_handler(state=MyStates.new_eng_word)
def handle_new_eng_word(message):
    cid = message.chat.id
    eng_word = message.text.strip()
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['new_eng_word'] = eng_word
    
    bot.send_message(cid, "Теперь введите перевод на русский язык:")
    bot.set_state(message.from_user.id, MyStates.new_ru_word, message.chat.id)

@bot.message_handler(state=MyStates.new_ru_word)
def handle_new_ru_word(message):
    cid = message.chat.id
    ru_word = message.text.strip()
    
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['new_ru_word'] = ru_word
    
    session = sessionmaker(bind=engine)()
    current_user = session.query(TGUsers).filter(TGUsers.tg_user_id == cid).one_or_none()
    if not current_user:
        bot.send_message(message.chat.id, "Ошибка: Пользователь не найден.")
        return
    
    new_word = Words(
        id_users=current_user.id,
        engword=data['new_eng_word'],
        ruword=data['new_ru_word']
    )
    
    session.add(new_word)
    session.commit()
    
    bot.send_message(cid, f"Слово '{data['new_eng_word']}' добавлено.")
    bot.delete_state(message.from_user.id, message.chat.id)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text
    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить слово 🇷🇺{data['translate_word']}")
    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)