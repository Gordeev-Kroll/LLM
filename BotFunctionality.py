import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext,CallbackQueryHandler
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update,InlineKeyboardButton, InlineKeyboardMarkup
from duckduckgo_search import DDGS
import ollama
import aiohttp
import re
import random
from sentence_transformers import SentenceTransformer
import numpy as np
from bs4 import BeautifulSoup
from aiohttp import ClientTimeout
import urllib.parse
from scipy.spatial.distance import cosine
MODEL = SentenceTransformer("all-MiniLM-L6-v2")

# Список популярных User-Agent для подделки
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
    "Mozilla/5.0 (Windows NT 6.3; rv:35.0) Gecko/20100101 Firefox/35.0"
]

COUNT_OF_SUBREQ = 10
COUNT_OF_LINKS = 2
REQUEST_STRING = f'Напиши {COUNT_OF_SUBREQ} подзапросов к запросу '


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("Search", callback_data="1"),
            InlineKeyboardButton("Help", callback_data="2"),
        ],
        [InlineKeyboardButton("Settings", callback_data="3")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери команду, дружище!", reply_markup=reply_markup)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    query = update.callback_query
    await query.answer()
    
    if query.data == "1":
        await search_command(update,context)
    elif query.data == "2":
        await help_command(update,context)
    elif query.data == "3":
        await setting_command(update,context)
    # await query.edit_message_text(text=f"Selected option: {query.data}")

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.callback_query.message.reply_text("Введите текст запроса:")
    context.user_data['awaiting_input'] = 'search'

    # await update.reply_text(text=f"Selected option: {str}")

    """
    response = ollama.chat(model='akdengi/saiga-llama3-8b', messages=[
  {
    'role': 'user',
    'content': f'{update.message.text}',
  },
    ])
   # print(response['message']['content'])
    await update.message.reply_text(response['message']['content'])
    """

async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_input') == 'search':
        
        user_input = update.message.text
        # -------------------------------------------------------
        response = ollama.chat(model='akdengi/saiga-llama3-8b', messages=[
        {
        'role': 'user',
        'content': f"{REQUEST_STRING} \"{user_input}\". Каждый подзапрос выведи под отдельным номером в столбик" ,
        },
        ])
       
        subrequests = parse_subreq(update,context, response['message']['content'])
      
       #print(subrequests)
        await update.message.reply_text(response['message']['content'])
        
        # await get_results(user_input,subrequests)

        # all_sourese = get_results(subrequests)
        # print(subrequests)
        # lts = []
        # for subreg in subrequests:
        #     lts.append(np.array(MODEL.encode(subreg)))

        # print(lts)
        # context.user_data['awaiting_input'] = None


async def get_results(main_request,subrequests):


    # print(subrequests)
    list_to_output = []
    main_emb = np.array(MODEL.encode(main_request))

    for req in subrequests:

        result_list = await duckduckgo_search(req)
        parsed_results = await text_search(result_list)
        # Фильтрация текстов длиной не менее 100 символов
        filtered_results = [result for result in parsed_results if len(result['text'].strip()) >= 100]
        print('=============================================================================================')
        print(filtered_results)
        print('=============================================================================================')

        # Разделение результатов на списки url и text
        urls = [result['url'] for result in filtered_results]
        texts = [result['text'] for result in filtered_results]
        results_emb = []
            # Эмбеддинги с текста по одному подзапросу
        for i in texts:
            results_emb.append(np.array(MODEL.encode(i)))

        print('=============================================================================================')
        print(results_emb)
        print('=============================================================================================')

        list_similarity = compare_embeddings(main_emb,results_emb)
        print('=============================================================================================')
        print(list_similarity)
        print('=============================================================================================')

        list_to_output.append(urls[list_similarity.index(max(list_similarity))])
        asyncio.sleep(random.uniform(1, 3))

    print(list_to_output)



def compare_embeddings(embedding, embeddings_list):
    list_sim = []
    for i, other_embedding in enumerate(embeddings_list):
        # Вычисляем косинусное расстояние
        similarity = 1 - cosine(embedding, other_embedding)
        list_sim.append(similarity)
    return list_sim

# Асинхронная функция для поиска на DuckDuckGo
# Асинхронная функция для поиска на DuckDuckGo
async def duckduckgo_search(query):
    url = f'https://html.duckduckgo.com/html/?t=h_&q={query}&ia=web'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            r = await response.text()
            soup = BeautifulSoup(r, 'lxml')
            a_tags = soup.find_all('a', class_='result__snippet')
            results = []
            for a_tag in a_tags:
                link = a_tag.get('href')
                if 'uddg=' in link:
                    query_params = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
                    if 'uddg' in query_params:
                        decoded_link = query_params['uddg'][0]
                        results.append(decoded_link)
            return results
        
# Вспомогательная функция для загрузки текста страницы
async def fetch_text(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                r = await response.text()
                soup = BeautifulSoup(r, 'lxml')

                # Получаем текст страницы
                text_elements = soup.find_all(['p', 'br'])
                text_list = [item.get_text(strip=True) for item in text_elements]
                cleaned_text = ' '.join([text for text in text_list if text])

                return {'url': url, 'text': cleaned_text}
            else:
                print(f"Ошибка: Статус ответа {response.status} для {url}")
                return {'url': url, 'text': ''}
    except Exception as e:
        print(f"Ошибка при доступе к {url}: {e}")
        return {'url': url, 'text': ''}

# Асинхронная функция для поиска текста по ссылкам
async def text_search(result_links):
    async with aiohttp.ClientSession(timeout=ClientTimeout(total=10)) as session:
        tasks = [fetch_text(session, url) for url in result_links]
        results = await asyncio.gather(*tasks)
        return results  

def parse_subreq(update: Update, context: ContextTypes.DEFAULT_TYPE, text):

    txt = text.replace('**','')
    pattern =  r'(\d+)\.\s+([^\d]+?\?)' 
    list = re.findall(pattern, txt, re.DOTALL)  # re.DOTALL позволяет . совпадать с \n
    list = [match[1].strip() for match in list]
    return list
   

    # print(text)
  

async def help_command(update, context):
    await update.callback_query.message.reply_text("Я умею выполнять следующие команды:\n"
                                    "Кнопка Search - Выполнить поисковой запрос\n"
                                    "Кнопка Help - Показать справку\n"
                                    "Кнопка Settings - Выпонить настройки для поисковой системы")



async def setting_command(update, context):
   await update.callback_query.message.reply_text("Выполнить настройку бота...")



async def bot_talking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response = ollama.chat(model='akdengi/saiga-llama3-8b', messages=[
  {
    'role': 'user',
    'content': f'{update.message.text}',
  },
    ])
   # print(response['message']['content'])
    await update.message.reply_text(response['message']['content'])

# Активировать модель через консоль  - ollama run akdengi/saiga-llama3-8b





"""
# Активировать модель через консоль  - ollama run akdengi/saiga-llama3-8b

# Старая реализация метода "start", которая просто предлагала выбор команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("/start"), KeyboardButton("/help")],
        [KeyboardButton("/newPicture"), KeyboardButton("/findInfo")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привет! Выберите команду:", reply_markup=reply_markup)

"""
"""

    keyboard = [
        [KeyboardButton("/search"), KeyboardButton("/help")],
        [KeyboardButton("/newPicture"), KeyboardButton("/setSettings")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Привет! Выберите команду:", reply_markup=reply_markup)
"""