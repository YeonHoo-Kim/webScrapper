import scrapy
import time
from huffpostScrap.items import HuffpostscrapCommentItem
from huffpostScrap.items import HuffpostscrapItem
from selenium import webdriver
from scrapy_selenium import SeleniumRequest
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


options = Options()
# options.add_argument('--headless') # headless모드 브라우저가 뜨지 않고 실행됩니다.
options.add_argument("--blink-setting=imagesEnable=false"); # 페이지 로딩에서 이미지 제외

class QuoteSpider(scrapy.Spider):
    # variables (name, start_url) should be this name
    # scrapy.Spider recognizes only with these names

    # name: spider name
    # start_urls: list of websites we want to scrap
    name = 'posts'
    start_urls = [
        'https://www.huffpost.com/archive/2021-01-01'
        # 'https://www.huffpost.com/entry/simone-biles-withdraws-floor-event_n_61061168e4b0f9b5a234254d#comments'
    ]

    def parse(self, response):
        cards = response.css('div.zone__content > div')
        for index, card in enumerate(cards):
            url = card.css('div.card__content > a::attr(href)').get()
            # print(f'link index of 2021-01-01: {0}')
            yield scrapy.Request(f'{url}#comments', callback=self.parse_posts)

    def parse_posts(self, response):
        # extract directly by css-selector
        # extract_first() method gets only text (not list)

        # can use response data directly from cmd
        # scrapy shell "http://quotes.toscrape.com/" -> check examples...

        item = HuffpostscrapItem()

        item['headline'] = response.css('h1.headline::text').get()
        item['dek'] = response.css('div.dek::text').get()
        item['author'] = response.css('h2.author-card__name > a.cet-internal-link > span::text').get()
        item['time'] = response.css('div.timestamp > time::attr(datetime)').get()
        
        # use selenium to retrieve a shadow dom (each drivers)
        driver = webdriver.Chrome('/Users/r14798/projects/web-scraper/huffpostScrap/chromedriver/chromedriver_mac_arm64', chrome_options=options)
        driver.get(f'{response.url}#comments')
        # print('Debuggin: Driver get Success!!!\n')
        # explicit wait
        shadow_parent = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#comments > div.comments__container > div > div"))
        )
        # print('Debuggin: WebDriverWait!!!\n')

        # get shadow element
        def expand_shadow_element(element):
            return driver.execute_script('return arguments[0].shadowRoot', element)
        shadow_root = expand_shadow_element(shadow_parent)

        # loop of click more comments button
        while True:
            try:
                more_comments_btn = shadow_root.find_element(By.CSS_SELECTOR, 'div.spcv_loadMoreCommentsContainer > button')
                ActionChains(driver).move_to_element(more_comments_btn).perform()
                more_comments_btn.click()
                time.sleep(5) # implicit wait
            except Exception as error:
                break
        
        def expand_more_element(css_selector):
            more_elements = shadow_root.find_elements(By.CSS_SELECTOR, css_selector)
            if(len(more_elements) == 0): 
                return False
            # print(f'More elements length: {len(more_elements)} with {css_selector}')
            for btn in more_elements:
                ActionChains(driver).move_to_element(btn).perform()
                btn.click()
                time.sleep(3) # implicit wait
            return True

        # show more replies (구조 상 show N replies와 N reply 버튼 섞임)
        while True:
            if expand_more_element('div.spcv_rootComment > button, div.spcv_isChildrenFetchedAlready > button') is False:
                break

        # expand comments (see more...)
        expand_more_element('div.src-entities-Text-TextEntity__text-entity > span')

        #comment containers    
        comments_el = shadow_root.find_elements(By.CSS_SELECTOR, '.spcv_messages-list .spcv_list-item > article')

        def set_comments(comments_array, comments_element):
            # print(f'This is set_comments {len(comments_element)}\n')
            for index, comment_container in enumerate(comments_element):
                # print(f'This is for loop {index}\n')
                comment = HuffpostscrapCommentItem()

                # Does comment violated policy?
                try:
                    comment['name'] = comment_container.find_element(By.CSS_SELECTOR, '.spcv_root-message .src-components-Username-index__wrapper').text
                    comment['time'] = comment_container.find_element(By.TAG_NAME, 'time').text
                    comment['text'] = comment_container.find_element(By.CSS_SELECTOR, '.src-entities-Text-TextEntity__text-entity').text
                    vote = comment_container.find_elements(By.CSS_SELECTOR, '.components-MessageActions-components-VoteButtons-index__votesCounter')
                    comment['thumbs_up'] = vote[0].text
                    comment['thumbs_down'] = vote[1].text
                except Exception as error:
                    # This comment violated our policy
                    comment['name'] = ""
                    comment['time'] = ""
                    comment['text'] = "This comment violated our policy"
                    comment['thumbs_up'] = "0"
                    comment['thumbs_down'] = "0"
                # Does comment has child?
                child_elements = comment_container.find_elements(By.CSS_SELECTOR, ':scope > div > div > ul > li')
                # print(f"There is a child for {index} with length: {len(child_elements)}\n")
                if len(child_elements) > 0:
                    comment['child'] = set_comments([], child_elements)
                else:
                    comment['child'] = []
                comments_array.append(comment)
            return comments_array

        item['comments'] = set_comments([], comments_el)
        driver.quit()
        yield item