import scrapy
import time
from huffpostScrap.items import HuffpostscrapItem
from scrapy_selenium import SeleniumRequest
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

options = Options()
# options.add_argument('--headless') #headless모드 브라우저가 뜨지 않고 실행됩니다.

class QuoteSpider(scrapy.Spider):
    # variables (name, start_url) should be this name
    # scrapy.Spider recognizes only with these names

    # name: spider name
    # start_urls: list of websites we want to scrap
    name = 'quotes'
    start_urls = ['https://www.huffpost.com/entry/anthony-fauci-covid-19-vaccine-mandates-quite-possible_n_5fef5542c5b6ec8ae0b2aa1f']
    
    # def start_requests(self):
    #     url = self.base_url
    #     yield SeleniumRequest(
    #         url=url, 
    #         callback=self.parse,
    #         # script="document.querySelector('.entry__content-and-right-rail-container .social-buttons__icons__item--comments').click();"
    #     )

    def parse(self, response):
        # extract directly by css-selector
        # extract_first() method gets only text (not list)

        # can use response data directly from cmd
        # scrapy shell "http://quotes.toscrape.com/" -> check examples...

        # examples... (id: "#", class: ".")
        # response.css("title::text").extract_first() ... get title tag's text (first one only)
        # response.css("span.text::text").extract() ... get span tag's texts with class = text
        # response.css("span.text::text")[1].extract() ... get span tag's 2nd text with class = text
        # response.css(".author::text").extract() ... get class author's text
        item = HuffpostscrapItem()

        item['headline'] = response.css('h1.headline::text').get()
        item['dek'] = response.css('div.dek::text').get()
        item['author'] = response.css('h2.author-card__name > a.cet-internal-link > span::text').get()
        item['time'] = response.css('div.timestamp > time').get()
        
        # use selenium to retrieve a shadow dom 
        from selenium import webdriver
        driver = webdriver.Chrome('/Users/r14798/projects/web-scraper/huffpostScrap/chromedriver/chromedriver_mac_arm64', chrome_options=options)

        driver.get(f'{self.start_urls[0]}#comments')
        # implicit wait
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#comments > div > div > div")))
        # driver.find_element(By.CSS_SELECTOR, '.entry__content-and-right-rail-container .social-buttons__icons__item--comments').click()
        # element.click()
        # WebDriverWait(element, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#comments > div > div > div')))

        shadow_parent = driver.find_element(By.CSS_SELECTOR, '#comments > div > div > div')
        # get shadow element
        def expand_shadow_element(element):
            return driver.execute_script('return arguments[0].shadowRoot', element)
        shadow_root = expand_shadow_element(shadow_parent)

        # loop of click more comments button
        while True:
            try:
                more_button = shadow_root.find_element(By.CSS_SELECTOR, 'div.spcv_loadMoreCommentsContainer > button')
                ActionChains(driver).move_to_element(more_button).perform()
                more_button.click()
                time.sleep(3) # implicit wait
            except Exception as error:
                break
            
        comments_el = shadow_root.find_elements(By.CSS_SELECTOR, 'li.spcv_list-item')
        comments = []

        # class Comment:
        #     def __init__(self):
        #         self.name = ""
        #         self.time = ""
        #         self.text = ""
        #         self.thumbs_up = 0
        #         self.thumbs_down = 0
        #         self.child_comment = {}

        for comment_el in comments_el:
            # comment = Comment()
            print(comment_el.find_element(By.CSS_SELECTOR, '.spcv_root-message .src-components-Username-index__wrapper').text)

        item['comments'] = comments_el
        driver.quit()
        yield item

        # for quote in response.css('div.quote'):
        #     item['text'] = quote.css('span.text::text').get()
        #     item['author'] = quote.css('small.author::text').get()
        #     item['tags'] = quote.css('div.tags a.tag::text').get()
        #     yield item