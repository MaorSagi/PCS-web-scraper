import mechanicalsoup


class Extractor:
    def __init__(self,id):
        self.browser = mechanicalsoup.Browser()
        self.id=id