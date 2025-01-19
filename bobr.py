import re
from sentence_transformers import SentenceTransformer
import asyncio
import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
import urllib.parse
import pandas as pd

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
async def fetch_text_and_metadata(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                r = await response.text()
                soup = BeautifulSoup(r, 'lxml')

                # Получаем текст страницы
                text_elements = soup.find_all(['p', 'br'])
                text_list = [item.get_text(strip=True) for item in text_elements]
                cleaned_text = ' '.join([text for text in text_list if text])

                # Получаем метаданные страницы
                title = soup.title.string if soup.title else 'No Title'

                return {'url': url, 'text': cleaned_text, 'title': title}
            else:
                print(f"Ошибка: Статус ответа {response.status} для {url}")
                return {'url': url, 'text': '', 'title': 'Error'}
    except Exception as e:
        print(f"Ошибка при доступе к {url}: {e}")
        return {'url': url, 'text': '', 'title': 'Error'}

# Асинхронная функция для поиска текста и метаданных по ссылкам
async def text_search(result_links):
    async with aiohttp.ClientSession(timeout=ClientTimeout(total=10)) as session:
        tasks = [fetch_text_and_metadata(session, url) for url in result_links]
        results = await asyncio.gather(*tasks)
        return results

# Главная функция для запуска асинхронных задач
async def main():
    query = input('Введите запрос: ')
    result_list = await duckduckgo_search(query)
    parsed_results = await text_search(result_list)

    # Фильтрация текстов длиной не менее 100 символов
    filtered_results = [result for result in parsed_results if len(result['text'].strip()) >= 100]

    # Разделение результатов на списки url и text
    urls = [result['url'] for result in filtered_results]
    texts = [result['text'] for result in filtered_results]

    # Печать результата
    for url, text in zip(urls, texts):
        print(f"URL: {url}")
        print(f"Text: {text[:100]}...")  # Печатаем первые 100 символов текста

    print(f"Количество записей: {len(filtered_results)}")

    for i in texts:
        print(i)
        print('---------------------')

    # Возвращение списков
    return urls, texts

# Создание эмбеддингов
def create_embeddings(texts):
    model = SentenceTransformer('all-MiniLM-L6-v2')  # Загружаем модель Sentence Transformers
    embeddings = model.encode(texts, show_progress_bar=True)  # Создаем эмбеддинги
    return embeddings

# Запуск программы
if __name__ == '__main__':
    urls_list, texts_list = asyncio.run(main())  # Получаем списки url и text
    if texts_list:
        embeddings_list = create_embeddings(texts_list)  # Создаем эмбеддинги
        print(f"Эмбеддинги успешно созданы. Всего: {len(embeddings_list)}")


