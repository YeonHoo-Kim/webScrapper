from huffpostScrap.spiders.quotes_spider import QuoteSpider
from scrapy.crawler import CrawlerProcess
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
def main():
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(QuoteSpider)
    process.start()

    
if __name__ == "__main__":
    main()

