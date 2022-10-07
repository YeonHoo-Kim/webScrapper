import scrapy

class QuoteSpider(scrapy.Spider):
    # variables (name, start_url) should be this name
    # scrapy.Spider recognizes only with these names

    # name: spider name
    # start_urls: list of websites we want to scrap
    name = 'quotes'
    start_urls = [
        'http://quotes.toscrape.com'
    ]

    def parse(self, response):
        # extract directly by css-selector
        # extract_first() method gets only text (not list)

        # can use response data directly from cmd
        # scrapy shell "http://quotes.toscrape.com/" -> check examples...

        # examples... (id: "#", class: ".")
        # response.css("title::text").extract_first() ... get title tag's text (first one only)
        # response.css("span.text::text").extract() ... get span tag's texts with class = text
        # response.css("span.text::text")[1].extract() ... get span tag's 2nd text with class = text

        title = response.css('title::text').extract() 
        yield {'titletext': title}
