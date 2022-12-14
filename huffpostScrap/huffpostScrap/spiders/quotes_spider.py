import platform
import scrapy
import threading
import time
from datetime import datetime, timedelta
from huffpostScrap.items import HuffpostscrapCommentItem
from huffpostScrap.items import HuffpostscrapItem
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

start_time = time.time()

options = Options()
options.add_argument('headless') # headless모드 브라우저가 뜨지 않고 실행됩니다.
options.add_argument("--blink-setting=imagesEnable=false"); # 페이지 로딩에서 이미지 제외
options.add_argument("disable-gpu") # gpu 비활성화

base_url = 'https://www.huffpost.com/archive'
url_list = []

# 시작일: start_date
# 종료일: end_date
start = '2022-04-21'
end = '2022-04-21'

start_date = datetime.strptime(start, "%Y-%m-%d")
end_date = datetime.strptime(end, "%Y-%m-%d")

# 종료일 까지 반복
while start_date <= end_date:
    dates = start_date.strftime("%Y-%m-%d")
    url_list.append(f'{base_url}/{dates}')
    # 하루 더하기
    start_date += timedelta(days=1)

# custom conditions wait until shadow dom is attached
class shadow_attached(object):
    def __init__(self, locator):
        print('\nshadow_attached custom expected conditions init \n')
        self.locator = locator

    def __call__(self, driver):
        element = driver.find_element(*self.locator)
        shadow = driver.execute_script('return arguments[0].shadowRoot', element)
        # 댓글 슬라이더에 conversation-footer 영역이 보이면 shadow dom이 rendered 됨으로 간주
        return len(shadow.find_elements(By.CSS_SELECTOR, 'div.spcv_conversation-footer')) > 0

# custom conditions to click button (show more comments)
class list_added(object):
    def __init__(self, locator, element, prev_len):
        self.locator = locator
        self.element = element
        self.prev_len = prev_len

    def __call__(self, driver):
        cur_len = len(self.element.find_elements(*self.locator))
        print(f'\n{cur_len} {self.prev_len}\n')
        return cur_len > self.prev_len

class QuoteSpider(scrapy.Spider):
    # variables (name, start_url) should be this name
    # scrapy.Spider recognizes only with these names

    # name: spider name
    # start_urls: list of websites we want to scrap
    name = 'posts'
    # start_urls = url_list
    start_urls = [
        # comments
        # 'https://www.huffpost.com/entry/ap-us-capitol-riot-misinformation-lies_n_61d05615e4b0bb04a6398a8f'
        'https://www.huffpost.com/entry/covid-rapid-test-swab-nose-throat_l_61cf6bbae4b0bcd219539517#comments'
        # 'https://www.huffpost.com/entry/sandia-peak-tram-people-stuck_n_61d0b532e4b0bcd2195410ca#comments'
        # 'https://www.huffpost.com/entry/ap-eu-austria-obit-gertrude-pressburger_n_61d0aaa6e4b0bcd219540b75#comments'
        # 'https://www.huffpost.com/entry/marine-corps-206-covid-vaccine-discharges_n_61d241e6e4b0bcd21954c1d4#comments'
        # 'https://www.huffpost.com/entry/us-supreme-court-stolen-painting_n_6261c4b5e4b0ea625c04dc73#comments'
        # no comments
        # 'https://www.huffpost.com/entry/kelly-ernby-dead-orange-county-da_n_61d43584e4b061afe3aa9d09#comments'
    ]
    custom_settings = {
        'CONCURRENT_REQUESTS': 30,
        'LOG_LEVEL': 'WARN',
        'FEEDS': {
            'posts.json': {
                'format': 'json'
            }
        },
        'FEED_EXPORT_ENCODING': 'utf-8'
    }

    def parse(self, response):
    #     cards = response.css('div.zone__content > div')
    #     for card in enumerate(cards):
    #         url = card.css('div.card__content > a::attr(href)').get()
    #         yield scrapy.Request(f'{url}#comments', callback=self.parse_posts)
    #     print("\n\n{:.2f} Seconds\n\n".format(time.time() - start_time))

    # def parse_posts(self, response):
        # extract directly by css-selector
        # extract_first() method gets only text (not list)

        # can use response data directly from cmd
        # scrapy shell "http://quotes.toscrape.com/" -> check examples...

        item = HuffpostscrapItem()

        item['label'] = response.css('header.entry__header > div.top-header > div.label a.label__link > span::text').get()
        item['headline'] = response.css('h1.headline::text').get()
        item['dek'] = response.css('div.dek::text').get()
        item['author'] = response.css('h2.author-card__name > a.cet-internal-link > span::text').get()
        if(item['author'] == None):
            item['author'] = response.css('span.entry-wirepartner__byline::text').get()
        item['time'] = response.css('div.timestamp > time::attr(datetime)').get()
        p_selectors = [
            '#entry-body h3 > strong::text',
            '#entry-body p::text',
            '#entry-body p > em::text',
            '#entry-body p > em > a::text',
            '#entry-body p > span::text',
            '#entry-body p > a::text',
            '#entry-body p > a > span::text',
        ]
        paragraphs = response.css(', '.join(p_selectors)).extract()
        item['contents'] = ' '.join(paragraphs)

        # use selenium to retrieve a shadow dom (each drivers)
        if(platform.system() == 'Windows'):
            driver = webdriver.Chrome('C:/Users/kywho/projects/webScrapper/huffpostScrap/chromedriver/chromedriver_windows', chrome_options=options)
        else:
            driver = webdriver.Chrome('/Users/r14798/projects/web-scraper/huffpostScrap/chromedriver/chromedriver_mac_arm64', chrome_options=options)
        driver.get(f'{response.url}#comments')
        print('\nDebuggin: Driver get Success!!!\n')
        # explicit wait
        try:
            WebDriverWait(driver, 10, 1).until(
                EC.all_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#comments > div.comments__container > div > div")),
                    shadow_attached((By.CSS_SELECTOR, "#comments > div.comments__container > div > div"))
                )
            )
            print('\nDebuggin: WebDriverWait!!!\n')
            
            # get shadow parent
            shadow_parent = driver.find_element(By.CSS_SELECTOR, "#comments > div.comments__container > div > div")

            # get shadow element
            def expand_shadow_element(element):
                return driver.execute_script('return arguments[0].shadowRoot', element)
            shadow_root = expand_shadow_element(shadow_parent)

            # loop of click more comments button
            print('\nDebuggin: click more comments button!!!\n')
            cur_len = 0
            while True:
                cur_len = len(shadow_root.find_elements(By.CSS_SELECTOR, 'ul.spcv_messages-list > li'))
                more_comments_btns = shadow_root.find_elements(By.CSS_SELECTOR, 'div.spcv_loadMoreCommentsContainer > button')
                if len(more_comments_btns) == 0:
                    break
                ActionChains(driver).move_to_element(more_comments_btns[0]).perform()
                print('\nScroll Success!!!\n')
                more_comments_btns[0].click()
                print('\nClick Success!!!\n')
                WebDriverWait(driver, 10).until(list_added((By.CSS_SELECTOR, 'ul.spcv_messages-list > li'), shadow_root, cur_len))
            
            # show more replies (구조 상 show N replies와 N reply 버튼 섞임)
            print('\nDebuggin: click more replies!!!\n')
            def expand_more_element(css_selector):
                more_elements = shadow_root.find_elements(By.CSS_SELECTOR, css_selector)
                if(len(more_elements) == 0): 
                    return False
                print(f'\nMore elements length: {len(more_elements)} with {css_selector}')
                for btn in more_elements:
                    ActionChains(driver).move_to_element(btn).perform()
                    btn.click()
                    # 버튼이 화면에 보이지 않을때까지 기다림
                    WebDriverWait(driver, 10).until(EC.invisibility_of_element(btn))
                return True
            while True:
                if expand_more_element('div.spcv_show-more-replies > button') is False:
                    break

            # expand comments (see more...)
            print('\nDebuggin: see more!!!\n')
            expand_more_element('div.src-entities-Text-TextEntity__text-entity > span')

            #comment containers    
            comments_el = shadow_root.find_elements(By.CSS_SELECTOR, '.spcv_messages-list .spcv_list-item > article')
            default_sel = ':scope > div.spcv_messageStackWrapper > div > div'

            def get_votes(vote_container):
                try:
                    up = vote_container.find_element(By.CSS_SELECTOR, ':scope > span span.components-MessageActions-components-VoteButtons-index__votesCounter').text
                except Exception as error:
                    # print('\nVote Up Error\n')
                    up = "0"
                try:
                    down = vote_container.find_element(By.CSS_SELECTOR, ':scope > button span.components-MessageActions-components-VoteButtons-index__votesCounter').text
                except Exception as error:
                    # print('\nVote Down Error\n')
                    down = "0"
                return [up, down]
            

            def set_comments(comments_array, comments_element):
                print(f'\nThis is set_comments {len(comments_element)}\n')
                for index, comment_container in enumerate(comments_element):
                    print(f'\nThis is for loop {index}\n')
                    comment = HuffpostscrapCommentItem()

                    # Does comment violated policy?
                    try:
                        comment['name'] = comment_container.find_element(By.CSS_SELECTOR, f'{default_sel} span.src-components-Username-index__wrapper').text
                        comment['time'] = comment_container.find_element(By.TAG_NAME, 'time').text
                        comment['text'] = comment_container.find_element(By.CSS_SELECTOR, f'{default_sel} div.src-entities-Text-TextEntity__text-entity').text
                        vote = comment_container.find_element(By.CSS_SELECTOR, f'{default_sel} div.components-MessageActions-components-VoteButtons-index__votesContainer')
                        vote_num = get_votes(vote)
                        comment['thumbs_up'] = vote_num[0]
                        comment['thumbs_down'] = vote_num[1]
                    except Exception as error:
                        # This comment violated our policy
                        print('\n Comment has been deleted or violated!!! \n')
                        comment['name'] = ""
                        comment['time'] = ""
                        comment['text'] = comment_container.find_element(By.CSS_SELECTOR, f'{default_sel} div.components-MessageContent-components-BlockedContent-index__blockedContent > span').text
                        comment['thumbs_up'] = "0"
                        comment['thumbs_down'] = "0"
                    # Does comment has child?
                    child_elements = comment_container.find_elements(By.CSS_SELECTOR, ':scope > div > div > ul > li')
                    print(f"\nThere is a child for {index} with length: {len(child_elements)}\n")
                    if len(child_elements) > 0:
                        comment['child'] = set_comments([], child_elements)
                    else:
                        comment['child'] = []
                    comments_array.append(comment)
                return comments_array

            item['comments'] = set_comments([], comments_el)
        except Exception as error:
            # no comments
            item['comments'] = []
        driver.quit()
        yield item

print(f'\nThreading Active count: {threading.active_count()}')
print(threading.enumerate())