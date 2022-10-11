# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class HuffpostscrapItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()

    # text = scrapy.Field()
    # author = scrapy.Field()
    # tags = scrapy.Field()

    headline = scrapy.Field()
    dek = scrapy.Field()
    author = scrapy.Field()
    time = scrapy.Field()
    comments = scrapy.Field()