import re
from sentence_transformers import SentenceTransformer
import asyncio
import aiohttp
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
import urllib.parse
import numpy as np
from scipy.spatial.distance import cosine
import pandas as pd

MODEL = SentenceTransformer("all-MiniLM-L6-v2")

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

def compare_embeddings(embedding, embeddings_list):
    list_sim = []
    for i, other_embedding in enumerate(embeddings_list):
        # Вычисляем косинусное расстояние
        similarity = 1 - cosine(embedding, other_embedding)
        list_sim.append(similarity)
    return list_sim

# Главная функция для запуска асинхронных задач
async def main():
    query = input('Введите запрос: ')
    result_list = duckduckgo_search(query)
    parsed_results = text_search(result_list)

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

    results_emb = []

    # Эмбеддинги с текста по одному подзапросу
    for i in texts:
        results_emb.append(np.array(MODEL.encode(i)))

    print(len(results_emb))
    print('=============================================================================================')
    print(results_emb)
    main_emb = np.array(MODEL.encode(query))
    print(main_emb)
    print('=============================================================================================')
    list_similarity = compare_embeddings(main_emb, results_emb)
    print(list_similarity)
    print('=============================================================================================')
    print(urls[list_similarity.index(max(list_similarity))])

    # Возвращение списков
    return urls, texts
    # Запуск программы


if __name__ == '__main__':
    main()

