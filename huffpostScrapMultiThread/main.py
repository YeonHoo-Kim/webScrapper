import concurrent.futures
import json
import platform
import requests
import time
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from multiprocessing import Pool
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

PROCESSES = 4
THREAD_MAX_WORKERS = 16

base_url = 'https://www.huffpost.com/archive'
date_list = []
posts = []

# 시작일: start_date
# 종료일: end_date
start = '2022-01-01'
end = '2022-01-01'

start_date = datetime.strptime(start, "%Y-%m-%d")
end_date = datetime.strptime(end, "%Y-%m-%d")

# 종료일 까지 반복
while start_date <= end_date:
    dates = start_date.strftime("%Y-%m-%d")
    date_list.append(dates)
    # 하루 더하기
    start_date += timedelta(days=1)

# custom conditions wait until shadow dom is attached
class shadow_attached(object):
    def __init__(self, locator):
        # print('\nshadow_attached custom expected conditions init \n')
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
        # print(f'\n list_addded: {cur_len} {self.prev_len}\n')
        return cur_len > self.prev_len

class Post:
    def __init__(self, label="", headline="", dek="", author="", time="", contents="", comments=[]):
        self.label = label
        self.headline = headline
        self.dek = dek
        self.author = author
        self.time = time
        self.contents = contents
        self.comments = comments
class Comment:
    def __init__(self, name="", time="", text="", thumbs_up="", thumbs_down="", child=[]):
        self.name = name
        self.time = time
        self.text = text
        self.thumbs_up = thumbs_up
        self.thumbs_down = thumbs_down
        self.child = child

##
# crawl given url with selenium driver
##
def crawl_with_url(url, driver):
    print('\nDebuggin: crawl with url start!!!\n')
    post = Post()
    driver.get(f'{url}#comments')
    post.label = driver.find_element(By.CSS_SELECTOR, 'header.entry__header > div.top-header > div.label a.label__link > span').text
    post.headline = driver.find_element(By.CSS_SELECTOR, 'h1.headline').text
    post.dek = driver.find_element(By.CSS_SELECTOR, 'div.dek').text
    try:
        post.author = driver.find_element(By.CSS_SELECTOR, 'h2.author-card__name > a.cet-internal-link > span').text
    except Exception as error:
        post.author = driver.find_element(By.CSS_SELECTOR, 'span.entry-wirepartner__byline').text
    post.time = driver.find_element(By.CSS_SELECTOR, 'div.timestamp > time').get_attribute('datetime')
    # p_selectors = [
    #     '#entry-body h3 > strong',
    #     '#entry-body p',
    #     '#entry-body p > em',
    #     '#entry-body p > em > a',
    #     '#entry-body p > span',
    #     '#entry-body p > a',
    #     '#entry-body p > a > span',
    # ]
    ps = driver.find_elements(By.CSS_SELECTOR, '#entry-body p, #entry-body h3')
    post.contents = ' '.join([x.text for x in ps])

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
            # print('\nScroll Success!!!\n')
            more_comments_btns[0].click()
            # print('\nClick Success!!!\n')
            try:
                WebDriverWait(driver, 10).until(list_added((By.CSS_SELECTOR, 'ul.spcv_messages-list > li'), shadow_root, cur_len))
            except Exception as error:
                print(error)
            
        # show more replies (구조 상 show N replies와 N reply 버튼 섞임)
        # 기존은 버튼이 사라지면 wait이 끝나는 구조였으나 6 replies -> show 1 replies 로 버튼이 사라지지 않는 코너케이스로 인해
        # child reply 개수가 증가하면 wait이 끝나는 구조로 변경 
        print('\nDebuggin: click more replies!!!\n')
        cur_len = 0
        while True:
            show_reply_btns = shadow_root.find_elements(By.CSS_SELECTOR, 'div.spcv_show-more-replies')
            if len(show_reply_btns) == 0:
                break
            for btn in show_reply_btns:
                btn_parent = btn.find_element(By.XPATH, '..')
                cur_len = len(btn_parent.find_elements(By.CSS_SELECTOR, ':scope > ul > li'))
                ActionChains(driver).move_to_element(btn).perform()
                btn.find_element(By.CSS_SELECTOR, ':scope > button').click()
                try:
                    WebDriverWait(driver, 10).until(list_added((By.CSS_SELECTOR, ':scope > ul > li'), btn_parent, cur_len))
                except Exception as error:
                    print(error)

        # expand comments (see more...)
        print('\nDebuggin: see more!!!\n')
        def expand_more_element(css_selector):
            more_elements = shadow_root.find_elements(By.CSS_SELECTOR, css_selector)
            if(len(more_elements) == 0): 
                return False
            # print(f'\nMore elements length: {len(more_elements)} with {css_selector}')
            for btn in more_elements:
                ActionChains(driver).move_to_element(btn).perform()
                btn.click()
                # reply loading time...
                # 버튼이 화면에 보이지 않을때까지 기다림
                try:
                    WebDriverWait(driver, 10).until(EC.staleness_of(btn))
                except Exception as error:
                    print(error)
            return True
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
            # print(f'\nThis is set_comments {len(comments_element)}\n')
            for index, comment_container in enumerate(comments_element):
                # print(f'\nThis is for loop {index}\n')
                comment = Comment()

                # Does comment violated policy?
                try:
                    comment.name = comment_container.find_element(By.CSS_SELECTOR, f'{default_sel} span.src-components-Username-index__wrapper').text
                    comment.time = comment_container.find_element(By.TAG_NAME, 'time').text
                    # get text and imgurl
                    texts = comment_container.find_element(By.CSS_SELECTOR, f'{default_sel} div.src-entities-MessageEntities-MessageEntities__message-entities')
                    texts = texts.find_elements(By.CSS_SELECTOR, ':scope > span > div, :scope > button > span > img')
                    new_str = []
                    for t in texts:
                        if t.get_attribute("src") != None:
                            new_str.append(t.get_attribute("src"))
                        else:
                            new_str.append(t.text)
                    comment.text = ' '.join(new_str)
                    vote = comment_container.find_element(By.CSS_SELECTOR, f'{default_sel} div.components-MessageActions-components-VoteButtons-index__votesContainer')
                    vote_num = get_votes(vote)
                    comment.thumbs_up = vote_num[0]
                    comment.thumbs_down = vote_num[1]
                except Exception as error:
                    # This comment violated our policy
                    # print('\n Comment has been deleted or violated!!! \n')
                    comment.name = ""
                    comment.time = ""
                    try:
                        comment.text = comment_container.find_element(By.CSS_SELECTOR, f'{default_sel} div.components-MessageContent-components-BlockedContent-index__blockedContent > span').text
                    except Exception as error:
                        print(error)
                        comment.text = "Error following text does not exist!"
                    comment.thumbs_up = "0"
                    comment.thumbs_down = "0"
                # Does comment has child?
                child_elements = comment_container.find_elements(By.CSS_SELECTOR, ':scope > div > div > ul > li')
                # print(f"\nThere is a child for {index} with length: {len(child_elements)}\n")
                if len(child_elements) > 0:
                    comment.child = set_comments([], child_elements)
                else:
                    comment.child = []
                comments_array.append(comment.__dict__)
            return comments_array
        post.comments = set_comments([], comments_el)
    except Exception as error:
        print(error)
        post.comments = []
    driver.quit()
    posts.append(post.__dict__)

##
# selenium driver setup
##
def driver_setup():
    options = Options()
    # options.add_argument('headless') # headless모드 브라우저가 뜨지 않고 실행됩니다.
    options.add_argument("disable-gpu") # gpu 비활성화

    if(platform.system() == 'Windows'):
        driver = webdriver.Chrome('C:/Users/kywho/projects/webScrapper/huffpostScrap/chromedriver/chromedriver_windows', options=options)
    else:
        driver = webdriver.Chrome('/Users/r14798/projects/web-scraper/huffpostScrap/chromedriver/chromedriver_mac_arm64', options=options)
    return driver
    # driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    # return driver
##
# assign tasks(crawl_with_url) to thread
##
def do_thread_assign(urls):
    thread_list = []
    with ThreadPoolExecutor(max_workers=THREAD_MAX_WORKERS) as executor:
        for url in urls:
            driver = driver_setup()
            thread_list.append(executor.submit(crawl_with_url, url, driver))
        for execution in concurrent.futures.as_completed(thread_list):
            execution.result()

# def do_process_assign(url):
#     do_thread_assign(url)

##
# Get Urls from archive page
# retrieve links from a tag (class: card)
##
def get_article_urls(url):
    print('\nDebuggin: get article urls start!!!\n')
    links = []
    req = requests.get(url)
    soup = BeautifulSoup(req.text, 'html.parser')
    a_tags = soup.select('div.card__content > a')
    for a_tag in a_tags:
        links.append(a_tag.get('href'))
    return links
    # return ['https://www.huffpost.com/entry/philadelphia-end-mask-mandate_n_6262063be4b07c34e9deba08']

if __name__ == "__main__":
    start_time = time.time()

    # with Pool(processes=PROCESSES) as pool:
    #     pool.map(do_process_allocate, url_list)

    print('\nDebuggin: archive crawl start!!!\n')

    for date in date_list:
        do_thread_assign(get_article_urls(f'{base_url}/{date}'))
        
        print(f'\nDebuggin: json outfile({date}) start!!!\n')
        # print(posts)
        with open(f'./posts_{date}.json', 'w', encoding='utf-8') as outfile:
            json.dump(posts, outfile, default=str, indent=4, ensure_ascii=False)
        print(f'\nDebuggin: json outfile({date}) end!!!\n')
    
    print('\nDebuggin: archive crawling finished!!!\n')
    
    print("--- elapsed time %s seconds ---" % (time.time() - start_time))