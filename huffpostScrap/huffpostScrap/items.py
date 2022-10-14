# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

# define the fields for your item here like:
# class Item(scrapy.Item):
    # name = scrapy.Field()

class HuffpostscrapItem(scrapy.Item):
    label = scrapy.Field()
    headline = scrapy.Field()
    dek = scrapy.Field()
    author = scrapy.Field()
    time = scrapy.Field()
    contents = scrapy.Field()
    comments = scrapy.Field()

class HuffpostscrapCommentItem(scrapy.Item):
    name = scrapy.Field()
    time = scrapy.Field()
    text = scrapy.Field()
    thumbs_up = scrapy.Field()
    thumbs_down = scrapy.Field()
    child = scrapy.Field()