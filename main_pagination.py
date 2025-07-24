import requests
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
import time
import os
import math
from datetime import datetime, timedelta
import logging
import brotli  # Убедитесь, что установлен: pip install brotli

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MVideoParser:
    def __init__(self):
        self.base_url = 'https://www.mvideo.ru'
        self.search_url = 'https://www.mvideo.ru/bff/products/v2/search'
        self.details_url = 'https://www.mvideo.ru/bff/product-details/list'
        self.prices_url = 'https://www.mvideo.ru/bff/products/prices'
        
        # Категории
        self.categories = {
            '36410': 'roboty-pylesosy',      # Роботы пылесосы
            '3088': 'vertikalnye-pylesosy',  # Вертикальные пылесосы  
            '470': 'feny'                    # Фены
        }
        
        # Фильтры
        self.filter_params_list = [
            'WyJicmFuZCIsIiIsImRyZWFtZSJd',           # ["brand","","dreame"]
            'WyJ0b2xrby12LW5hbGljaGlpIiwiIiwiZGEiXQ==' # ["tolko-v-nalichii","","da"]
        ]
        
        # Конфигурационный файл
        self.config_file = 'config.json'
        
    def get_fresh_session_and_headers(self):
        """Получить свежую сессию с актуальными cookies и headers"""
        logging.info("[+] Getting fresh session with Selenium...")
        
        # Настройки Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Proxy для PythonAnywhere
        proxy_url = "http://proxy.server:3128"
        
        driver = None
        try:
            # Проверяем, запущен ли скрипт на PythonAnywhere
            if 'PYTHONANYWHERE_DOMAIN' in os.environ:
                # Добавляем прокси для Selenium
                logging.info(f"[+] Using proxy for Selenium: {proxy_url}")
                chrome_options.add_argument(f'--proxy-server={proxy_url}')
                # На сервере используем предустановленный chromedriver
                service = ChromeService(executable_path='/usr/bin/chromedriver')
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # На локальном компьютере все остается как было
                driver = webdriver.Chrome(options=chrome_options)
            
            # Заходим на сайт
            logging.info("[+] Loading main page...")
            driver.get(self.base_url)
            time.sleep(5)
            
            # Скроллим немного
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(2)
            
            # Получаем cookies
            selenium_cookies = driver.get_cookies()
            cookies_dict = {}
            for cookie in selenium_cookies:
                cookies_dict[cookie['name']] = cookie['value']
            
            # Получаем User-Agent
            user_agent = driver.execute_script("return navigator.userAgent;")
            
            # Основные заголовки
            headers = {
                'User-Agent': user_agent,
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',  # Поддержка Brotli
                'Referer': self.base_url + '/',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }
            
            # Создаем сессию
            session = requests.Session()
            session.headers.update(headers)
            
            # Добавляем прокси для requests, если на сервере
            if 'PYTHONANYWHERE_DOMAIN' in os.environ:
                logging.info(f"[+] Using proxy for requests: {proxy_url}")
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url,
                }
                session.proxies.update(proxies)
            
            # Добавляем cookies в сессию
            for name, value in cookies_dict.items():
                session.cookies.set(name, value)
            
            logging.info("[+] Fresh session created successfully")
            return session, headers, cookies_dict
            
        except Exception as e:
            logging.error(f"[!] Error creating session: {e}")
            return self.get_basic_session()
        finally:
            if driver:
                driver.quit()
    
    def get_basic_session(self):
        """Создать базовую сессию с минимальными заголовками"""
        logging.info("[!] Using basic session...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',  # Поддержка Brotli
            'Referer': self.base_url + '/',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
        }
        
        session = requests.Session()
        session.headers.update(headers)
        
        # Добавляем прокси для requests, если на сервере
        if 'PYTHONANYWHERE_DOMAIN' in os.environ:
            proxy_url = "http://proxy.server:3128"
            proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
            session.proxies.update(proxies)
            
        return session, headers, {}
    
    def save_config(self, headers, cookies):
        """Сохранить конфигурацию"""
        config = {
            'headers': headers,
            'cookies': cookies,
            'timestamp': datetime.now().isoformat(),
            'expires': (datetime.now() + timedelta(hours=6)).isoformat()
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        logging.info(f"[+] Config saved to {self.config_file}")
    
    def load_config(self):
        """Загрузить сохраненную конфигурацию"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Проверяем срок годности
                expires_str = config.get('expires')
                if expires_str:
                    expires = datetime.fromisoformat(expires_str)
                    if datetime.now() < expires:
                        logging.info("[+] Using cached config")
                        headers = config.get('headers', {})
                        cookies = config.get('cookies', {})
                        
                        # Создаем сессию с кэшированными данными
                        session = requests.Session()
                        session.headers.update(headers)
                        for name, value in cookies.items():
                            session.cookies.set(name, value)
                            
                        return session, headers, cookies
                
                logging.info("[!] Config expired")
            except Exception as e:
                logging.error(f"[!] Error loading config: {e}")
        
        return None, None, None
    
    def decompress_response(self, response):
        """Распаковать ответ, если он сжат"""
        content_encoding = response.headers.get('content-encoding', '').lower()
        
        if content_encoding == 'br':
            try:
                # requests обычно автоматически распаковывает br, если правильно указан Accept-Encoding
                # Если response.text уже распакован, возвращаем его
                # Попробуем сначала вернуть response.text, если это не сработает, пробуем brotli
                if response.text and not response.text.startswith('{') and not response.text.startswith('['):
                    # Возможно, текст не распаковался автоматически, пробуем вручную
                    try:
                        decompressed = brotli.decompress(response.content)
                        return decompressed.decode('utf-8')
                    except Exception as e:
                        logging.error(f"[!] Error manual decompressing Brotli: {e}")
                        # Если и ручная распаковка не удалась, возвращаем то, что есть
                        return response.text
                else:
                    # response.text уже содержит распакованный JSON
                    return response.text
            except Exception as e:
                logging.error(f"[!] Error decompressing Brotli: {e}")
                return response.text
        elif content_encoding == 'gzip':
            # requests автоматически распаковывает gzip
            return response.text
        else:
            return response.text
    
    def debug_response(self, response, url):
        """Отладка ответа от сервера"""
        logging.info(f"Debug response from {url}")
        logging.info(f"Status code: {response.status_code}")
        logging.info(f"Headers: {dict(response.headers)}")
        
        content_encoding = response.headers.get('content-encoding', 'none')
        logging.info(f"Content-Encoding: {content_encoding}")
        
        try:
            # Распаковываем содержимое
            decompressed_content = self.decompress_response(response)
            content_preview = decompressed_content[:500]  # Первые 500 символов
            logging.info(f"Content preview: {content_preview}")
        except Exception as e:
            logging.error(f"Error processing content: {e}")
    
    def get_category_data(self, session, category_id, category_name):
        """Получить данные для одной категории"""
        logging.info(f'[+] Processing category: {category_name} (ID: {category_id})')
        
        params = {
            'categoryIds': category_id,
            'offset': '0',
            'filterParams': self.filter_params_list,
            'limit': '36',
            'doTranslit': 'true',
            'context': 'v2dzaG9wX2lkZFMwMDJsY2F0ZWdvcnlfaWRzn2QzMDg4/2ZjYXRfSWRkMjQzOP8=',
        }

        # Получаем общее количество товаров
        try:
            logging.info(f"[+] Making request to: {self.search_url}")
            
            response = session.get(self.search_url, params=params, timeout=30)
            
            # Отладка ответа
            # self.debug_response(response, self.search_url) # Закомментировано для уменьшения логов
            
            # Проверяем Content-Type
            content_type = response.headers.get('content-type', '')
            logging.info(f"Content-Type: {content_type}")
            
            if 'application/json' not in content_type.lower():
                logging.error(f"[!] Expected JSON, got: {content_type}")
                return None, None, None
            
            # Распаковываем и парсим JSON
            decompressed_text = self.decompress_response(response)
            response_data = json.loads(decompressed_text)
            logging.info(f"[+] Response received successfully")
            
        except requests.exceptions.RequestException as e:
            logging.error(f'[!] Request error for category {category_name}: {e}')
            return None, None, None
        except json.JSONDecodeError as e:
            logging.error(f'[!] JSON decode error for category {category_name}: {e}')
            try:
                decompressed_text = self.decompress_response(response)
                logging.error(f'[!] Response content: {decompressed_text[:500]}')
            except:
                logging.error(f'[!] Could not decode response content')
            return None, None, None
        except Exception as e:
            logging.error(f'[!] Unexpected error for category {category_name}: {e}')
            return None, None, None
            
        total_items = response_data.get('body', {}).get('total')
        if total_items is None:
            logging.warning(f'[!] No items in category {category_name}')
            logging.info(f'[!] Response  {response_data}')
            return None, None, None
            
        page_count = math.ceil(total_items / 36)
        logging.info(f'[+] Category {category_name}: Total items: {total_items}, Page count: {page_count}')

        products_ids = {}
        products_descriptions = {}
        products_prices = {}
        
        # Обработка страниц
        for i in range(min(page_count, 3)):  # Ограничиваем 3 страницами для теста
            logging.info(f'[+] Category {category_name}: Processing page {i + 1}/{page_count}')
            
            offset = f'{i * 36}'
            params['offset'] = offset
            
            # Добавляем случайную задержку
            time.sleep(2 + (i * 1))
            
            # Поиск товаров
            try:
                response = session.get(self.search_url, params=params, timeout=30)
                
                # Распаковываем и парсим JSON
                decompressed_text = self.decompress_response(response)
                content_type = response.headers.get('content-encoding', '')
                if 'application/json' not in response.headers.get('content-type', '').lower():
                    logging.error(f"[!] Expected JSON, got: {content_type}")
                    continue
                
                search_data = json.loads(decompressed_text)
            except Exception as e:
                logging.error(f'[!] Error fetching page {i} of category {category_name}: {e}')
                continue
                
            products_ids_list = search_data.get('body', {}).get('products', [])
            products_ids[i] = products_ids_list
            
            if not products_ids_list:
                continue
                
            # Получение описаний
            json_data = {
                'productIds': products_ids_list,
                'mediaTypes': ['images'],
                'category': True,
                'status': True,
                'brand': True,
                'propertyTypes': ['KEY'],
                'propertiesConfig': {'propertiesPortionSize': 5},
            }
            
            try:
                response = session.post(self.details_url, json=json_data, timeout=30)
                decompressed_text = self.decompress_response(response)
                products_descriptions[i] = json.loads(decompressed_text)
            except Exception as e:
                logging.error(f'[!] Error getting descriptions for page {i} of category {category_name}: {e}')
                products_descriptions[i] = {}

            # Получение цен
            products_ids_str = ','.join(products_ids_list)
            price_params = {
                'productIds': products_ids_str,
                'addBonusRubles': 'true',
                'isPromoApplied': 'true',
            }
            
            try:
                response = session.get(self.prices_url, params=price_params, timeout=30)
                decompressed_text = self.decompress_response(response)
                price_data = json.loads(decompressed_text)
                material_prices = price_data.get('body', {}).get('materialPrices', [])
                
                for item in material_prices:
                    price_info = item.get('price', {})
                    bonus_info = item.get('bonusRubles', {})
                    
                    item_id = price_info.get('productId')
                    if item_id:
                        products_prices[item_id] = {
                            'item_basePrice': price_info.get('basePrice'),
                            'item_salePrice': price_info.get('salePrice'),
                            'item_bonus': bonus_info.get('total')
                        }
            except Exception as e:
                logging.error(f'[!] Error getting prices for page {i} of category {category_name}: {e}')

        return products_ids, products_descriptions, products_prices

    def save_category_data(self, category_id, category_name, products_ids, products_descriptions, products_prices):
        """Сохранить данные категории"""
        if not os.path.exists('data'):
            os.makedirs('data')
        
        category_folder = f'data/{category_name}_{category_id}'
        if not os.path.exists(category_folder):
            os.makedirs(category_folder)
        
        # Сохранение данных по отдельности
        with open(f'{category_folder}/1_product_ids.json', 'w', encoding='utf-8') as file:
            json.dump(products_ids, file, ensure_ascii=False, indent=4)

        with open(f'{category_folder}/2_product_description.json', 'w', encoding='utf-8') as file:
            json.dump(products_descriptions, file, ensure_ascii=False, indent=4)

        with open(f'{category_folder}/3_product_prices.json', 'w', encoding='utf-8') as file:
            json.dump(products_prices, file, ensure_ascii=False, indent=4)
        
        # Создание общего файла для категории (объединение данных)
        try:
            # Собираем все товары из категории в один список
            category_products = []
            
            # Проходим по всем страницам с описаниями
            for page_data in products_descriptions.values():
                products = page_data.get('body', {}).get('products', [])
                for item in products:
                    product_id = item.get('productId')
                    
                    # Добавляем ценовую информацию, если она есть
                    if product_id and product_id in products_prices:
                        price = products_prices[product_id]
                        item['item_basePrice'] = price.get('item_basePrice')
                        item['item_salePrice'] = price.get('item_salePrice')
                        item['item_bonus'] = price.get('item_bonus')
                        translit_name = item.get("nameTranslit", "")
                        item['item_link'] = f'https://www.mvideo.ru/products/{translit_name}-{product_id}'
                    
                    # Добавляем информацию о категории
                    item['category_id'] = category_id
                    item['category_name'] = category_name
                    
                    category_products.append(item)
            
            # Сохраняем общий файл для категории
            category_result = {
                'total_products': len(category_products),
                'category_id': category_id,
                'category_name': category_name,
                'products': category_products,
                'generated_at': datetime.now().isoformat()
            }
            
            with open(f'{category_folder}/4_category_result.json', 'w', encoding='utf-8') as file:
                json.dump(category_result, file, ensure_ascii=False, indent=4)
                
            logging.info(f'[+] Category {category_name} data saved ({len(category_products)} products)')
            
        except Exception as e:
            logging.error(f'[!] Error creating combined file for category {category_name}: {e}')

    def get_result(self):
        """Генерация финальных результатов"""
        try:
            if not os.path.exists('data'):
                logging.info('[!] Data folder not found')
                return
                
            all_products_combined = []
            
            # Обрабатываем каждую категорию
            for category_id, category_name in self.categories.items():
                category_folder = f'data/{category_name}_{category_id}'
                
                if not os.path.exists(category_folder):
                    continue
                    
                # Загружаем описания
                desc_file = f'{category_folder}/2_product_description.json'
                prices_file = f'{category_folder}/3_product_prices.json'
                
                if not os.path.exists(desc_file) or not os.path.exists(prices_file):
                    continue
                
                with open(desc_file, 'r', encoding='utf-8') as file:
                    product_data = json.load(file)

                with open(prices_file, 'r', encoding='utf-8') as file:
                    product_price = json.load(file) 

                # Обработка данных
                for page_data in product_data.values():
                    products = page_data.get('body', {}).get('products', [])  
                    for item in products:
                        product_id = item.get('productId')
                        
                        if product_id and product_id in product_price:
                            price = product_price[product_id]
                            item['item_basePrice'] = price.get('item_basePrice')
                            item['item_salePrice'] = price.get('item_salePrice')
                            item['item_bonus'] = price.get('item_bonus')
                            translit_name = item.get("nameTranslit", "")
                            item['item_link'] = f'https://www.mvideo.ru/products/{translit_name}-{product_id}'
                            item['category_id'] = category_id
                            item['category_name'] = category_name
                            
                            all_products_combined.append(item)

            # Сохраняем общий результат
            with open('data/4_all_products_combined.json', 'w', encoding='utf-8') as file:
                json.dump({
                    'total_products': len(all_products_combined),
                    'categories': list(self.categories.values()),
                    'products': all_products_combined,
                    'generated_at': datetime.now().isoformat()
                }, file, ensure_ascii=False, indent=4)
                
            logging.info(f'[+] Combined result: {len(all_products_combined)} products from all categories')
            
        except Exception as e:
            logging.error(f'[!] Error in get_result: {e}')

    def run(self):
        """Основной метод запуска парсера"""
        logging.info("=== MVideo Parser Started ===")
        
        # Пытаемся загрузить сохраненную конфигурацию
        session, headers, cookies = self.load_config()
        
        if session is None:
            # Получаем свежую сессию
            session, headers, cookies = self.get_fresh_session_and_headers()
            # Сохраняем конфигурацию
            if headers and cookies:  # Только если есть данные
                self.save_config(headers, cookies)
        
        # Тестовый запрос для проверки работы
        logging.info("[+] Testing session...")
        try:
            test_response = session.get(self.base_url, timeout=10)
            logging.info(f"[+] Test request status: {test_response.status_code}")
        except Exception as e:
            logging.error(f"[!] Test request failed: {e}")
        
        # Обработка каждой категории
        for category_id, category_name in self.categories.items():
            try:
                products_ids, products_descriptions, products_prices = self.get_category_data(
                    session, category_id, category_name
                )
                
                if products_ids is not None:
                    self.save_category_data(
                        category_id, category_name, 
                        products_ids, products_descriptions, products_prices
                    )
                else:
                    logging.warning(f'[!] Failed to process category: {category_name}')
                    
            except Exception as e:
                logging.error(f'[!] Critical error processing category {category_name}: {e}')
                continue
        
        # Генерация финальных результатов
        self.get_result()
        logging.info("=== MVideo Parser Completed ===")

def main():
    parser = MVideoParser()
    try:
        parser.run()
    except KeyboardInterrupt:
        logging.info("\n[!] Parser interrupted by user")
    except Exception as e:
        logging.error(f'[!] Critical error: {e}')

if __name__ == "__main__":
    main()
