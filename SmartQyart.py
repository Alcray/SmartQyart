import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
import asyncio
import random
import sqlite3

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

conn = sqlite3.connect('quiz_bot.db', check_same_thread=False)
cursor = conn.cursor()

def init_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            rating INTEGER DEFAULT 1000
        )
    ''')
    conn.commit()

def get_title(rating):
    if rating >= 2000:
        return 'Grandmaster'
    elif rating >= 1800:
        return 'Master'
    elif rating >= 1600:
        return 'Expert'
    elif rating >= 1400:
        return 'Apprentice'
    else:
        return 'Novice'

questions_list = [
    {
        'question': 'What is the derivative of sin(x)?',
        'options': ['cos(x)', '-sin(x)', '-cos(x)', 'tan(x)'],
        'answer': 'cos(x)'
    },
    {
        'question': 'What is the integral of 1/x dx?',
        'options': ['x', 'ln(x)', 'e^x', 'x²/2'],
        'answer': 'ln(x)'
    },
    {
        'question': 'What is the value of the mathematical constant e approximately?',
        'options': ['2.71', '3.14', '1.62', '0.577'],
        'answer': '2.71'
    },
    {
        'question': 'Solve for x: 2x² - 8x + 6 = 0',
        'options': ['x = 1 or x = 3', 'x = -1 or x = 3', 'x = 2 or x = 1', 'x = 1 or x = 2'],
        'answer': 'x = 1 or x = 3'
    },
    {
        'question': 'What is the limit of (1 + 1/n)^n as n approaches infinity?',
        'options': ['1', '2', 'e', '∞'],
        'answer': 'e'
    },
    {
        'question': 'If f(x) = x² + 3x + 5, what is f\'(x)?',
        'options': ['2x + 3', 'x² + 3', '2x', 'x + 3'],
        'answer': '2x + 3'
    },
    {
        'question': 'What is the solution to the differential equation dy/dx = y?',
        'options': ['y = x²', 'y = ln(x)', 'y = e^x', 'y = Ce^x'],
        'answer': 'y = Ce^x'
    },
    {
        'question': 'What is the sum of the infinite geometric series 1 + 1/2 + 1/4 + 1/8 + ... ?',
        'options': ['1', '2', '3', '4'],
        'answer': '2'
    },
    {
        'question': 'What is the determinant of the matrix [[1, 2], [3, 4]]?',
        'options': ['-2', '0', '2', '10'],
        'answer': '-2'
    },
    {
        'question': 'What is the area under the curve y = x² from x = 0 to x = 1?',
        'options': ['1', '1/3', '1/2', '1/4'],
        'answer': '1/3'
    },
    {
        'question': 'Solve for x: log(x) = 3',
        'options': ['x = 100', 'x = 1000', 'x = 3', 'x = 10'],
        'answer': 'x = 1000'
    },
    {
        'question': 'What is the value of the Riemann zeta function ζ(2)?',
        'options': ['π²/6', 'π²', 'π/6', 'π³/6'],
        'answer': 'π²/6'
    },
    {
        'question': 'What is the sum of the first 100 positive integers?',
        'options': ['5050', '5000', '1000', '50500'],
        'answer': '5050'
    },
    {
        'question': 'What is the factorial of 6?',
        'options': ['720', '120', '5040', '360'],
        'answer': '720'
    },
    {
        'question': 'If the radius of a circle is doubled, how does the area change?',
        'options': ['Doubles', 'Quadruples', 'Triples', 'Stays the same'],
        'answer': 'Quadruples'
    },
    {
        'question': 'What is the value of cos(π/3)?',
        'options': ['1/2', '√3/2', '0', '-1'],
        'answer': '1/2'
    },
    {
        'question': 'What is the inverse function of f(x) = 2x + 3?',
        'options': ['f⁻¹(x) = (x - 3)/2', 'f⁻¹(x) = (x + 3)/2', 'f⁻¹(x) = 2/(x + 3)', 'f⁻¹(x) = 2x - 3'],
        'answer': 'f⁻¹(x) = (x - 3)/2'
    },
    {
        'question': 'Solve for x: e^x = 5',
        'options': ['x = ln(5)', 'x = 5', 'x = e', 'x = e/5'],
        'answer': 'x = ln(5)'
    },
    {
        'question': 'What is the derivative of x³?',
        'options': ['3x²', '3x', 'x²', '2x²'],
        'answer': '3x²'
    },
    {
        'question': 'What is the solution to the equation x² - 4 = 0?',
        'options': ['x = 2', 'x = -2', 'x = 2 or -2', 'x = 4'],
        'answer': 'x = 2 or -2'
    }
]


waiting_users = []
active_duels = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user.id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute('INSERT INTO users (user_id, username) VALUES (?, ?)', (user.id, user.username))
        conn.commit()
        await update.message.reply_text('Welcome to the Quiz Duel Bot!')
    else:
        await update.message.reply_text('Welcome back to the Quiz Duel Bot!')

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    # Check if user is already in a duel
    for duel in active_duels.values():
        if duel['user1_id'] == user_id or duel['user2_id'] == user_id:
            await update.message.reply_text('You are already in a duel!')
            return

    # Check if user is waiting
    if user_id in waiting_users:
        await update.message.reply_text('You are already waiting for a duel!')
        return

    if waiting_users:
        opponent_id = waiting_users.pop(0)
        # Start a duel
        duel_id = len(active_duels) + 1
        duel = {
            'user1_id': opponent_id,
            'user2_id': user_id,
            'current_question': 0,
            'questions': random.sample(questions_list, 3),
            'scores': {opponent_id: 0, user_id: 0},
            'answered': False,
            'attempted_users': set(),
            'message_ids': {}
        }
        active_duels[duel_id] = duel

        # Notify both users
        opponent_chat = await context.bot.get_chat(opponent_id)
        await context.bot.send_message(chat_id=opponent_id, text='Duel started with @{}!'.format(user.username or user.first_name))
        await update.message.reply_text('Duel started with @{}!'.format(opponent_chat.username or opponent_chat.first_name))

        # Send first question
        await send_question(context, duel_id)
    else:
        waiting_users.append(user_id)
        await update.message.reply_text('Waiting for an opponent...')

async def send_question(context, duel_id):
    duel = active_duels.get(duel_id)
    if not duel:
        return

    if duel['current_question'] >= 3:
        # End the duel
        await end_duel(context, duel_id)
        return

    # Delete previous messages if they exist
    for uid, message_id in duel['message_ids'].items():
        try:
            await context.bot.delete_message(chat_id=uid, message_id=message_id)
        except Exception as e:
            logging.warning(f"Failed to delete message {message_id}: {e}")

    question_data = duel['questions'][duel['current_question']]
    question = question_data['question']
    options = question_data['options']

    # Create inline keyboard
    keyboard = []
    for option in options:
        keyboard.append([InlineKeyboardButton(option, callback_data=option)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send question to both users
    user1_id = duel['user1_id']
    user2_id = duel['user2_id']
    duel['answered'] = False  # Reset answered flag
    duel['attempted_users'] = set()

    # Track messages to delete/edit later
    question_number = duel['current_question'] + 1
    message1 = await context.bot.send_message(chat_id=user1_id, text=f'Question {question_number}: {question}', reply_markup=reply_markup)
    message2 = await context.bot.send_message(chat_id=user2_id, text=f'Question {question_number}: {question}', reply_markup=reply_markup)

    duel['message_ids'] = {user1_id: message1.message_id, user2_id: message2.message_id}

async def handle_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    answer = query.data
    await query.answer()  # Acknowledge the callback

    # Find the duel the user is in
    for duel_id, duel in active_duels.items():
        if user_id == duel['user1_id'] or user_id == duel['user2_id']:
            # Check if the question message id matches
            message_id = duel['message_ids'].get(user_id)
            if message_id != query.message.message_id:
                return

            if duel['answered']:
                return
            if user_id in duel['attempted_users']:
                return

            duel['attempted_users'].add(user_id)
            current_question = duel['questions'][duel['current_question']]
            correct_answer = current_question['answer']

            if answer == correct_answer:
                duel['scores'][user_id] += 1
                duel['answered'] = True
                opponent_id = duel['user1_id'] if user_id == duel['user2_id'] else duel['user2_id']
                await context.bot.send_message(chat_id=user_id, text='Correct! You got the point.')
                opponent_name = (await context.bot.get_chat(user_id)).first_name
                await context.bot.send_message(chat_id=opponent_id, text=f'{opponent_name} answered correctly.')

                # Delete both users' messages
                await context.bot.delete_message(chat_id=user_id, message_id=query.message.message_id)
                opponent_message_id = duel['message_ids'].get(opponent_id)
                if opponent_message_id:
                    await context.bot.delete_message(chat_id=opponent_id, message_id=opponent_message_id)

                duel['current_question'] += 1
                duel['attempted_users'] = set()
                await asyncio.sleep(1)
                await send_question(context, duel_id)
                return
            else:
                await context.bot.send_message(chat_id=user_id, text='Incorrect answer.')

                if len(duel['attempted_users']) == 2:
                    for uid in [duel['user1_id'], duel['user2_id']]:
                        msg_id = duel['message_ids'].get(uid)
                        if msg_id:
                            await context.bot.delete_message(chat_id=uid, message_id=msg_id)

                    duel['current_question'] += 1
                    duel['attempted_users'] = set()
                    await asyncio.sleep(1)
                    await send_question(context, duel_id)
                return

async def end_duel(context, duel_id):
    duel = active_duels.pop(duel_id, None)
    if not duel:
        return
    user1_id = duel['user1_id']
    user2_id = duel['user2_id']
    scores = duel['scores']
    user1_score = scores[user1_id]
    user2_score = scores[user2_id]

    # Delete any remaining question messages
    for uid in [user1_id, user2_id]:
        msg_id = duel['message_ids'].get(uid)
        if msg_id:
            try:
                await context.bot.delete_message(chat_id=uid, message_id=msg_id)
            except:
                pass

    if user1_score > user2_score:
        winner_id = user1_id
        loser_id = user2_id
        result_text = 'Duel over! {} wins with a score of {} to {}.'.format((await context.bot.get_chat(user1_id)).first_name, user1_score, user2_score)
    elif user2_score > user1_score:
        winner_id = user2_id
        loser_id = user1_id
        result_text = 'Duel over! {} wins with a score of {} to {}.'.format((await context.bot.get_chat(user2_id)).first_name, user2_score, user1_score)
    else:
        result_text = 'Duel over! It\'s a tie with a score of {} to {}.'.format(user1_score, user2_score)

    if winner_id:
        cursor.execute('UPDATE users SET rating = rating + 10 WHERE user_id = ?', (winner_id,))
        cursor.execute('UPDATE users SET rating = rating - 10 WHERE user_id = ?', (loser_id,))
    conn.commit()

    await context.bot.send_message(chat_id=user1_id, text=result_text)
    await context.bot.send_message(chat_id=user2_id, text=result_text)

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute('SELECT username, rating FROM users ORDER BY rating DESC LIMIT 10')
    results = cursor.fetchall()
    text = '🏆 Leaderboard 🏆\n\n'
    for i, (username, rating) in enumerate(results, start=1):
        text += '{}. @{} - {}\n'.format(i, username or 'Anonymous', rating)
    await update.message.reply_text(text)

async def rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute('SELECT rating FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        rating = result[0]
        title = get_title(rating)
        await update.message.reply_text('Your rating: {}\nYour title: {}'.format(rating, title))
    else:
        await update.message.reply_text('You are not registered yet. Send /start to register.')

def main():
    init_db()
    application = ApplicationBuilder().token('7587237355:AAEhqITXcphKgTzu-xcWAmUOtM2ukxGNgZg').build()

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('duel', duel))
    application.add_handler(CommandHandler('leaderboard', leaderboard))
    application.add_handler(CommandHandler('rating', rating))
    application.add_handler(CallbackQueryHandler(handle_answer_callback))

    application.run_polling()

if __name__ == '__main__':
    main()
