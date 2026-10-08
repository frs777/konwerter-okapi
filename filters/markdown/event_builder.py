from dataclasses import replace
from core.events.builder import EventBuilder
from core.text_fragment.inline_code_finder import InlineCodeFinder

class MarkdownEventBuilder(EventBuilder):
    def __init__(self, code_finder=None):
        super().__init__()
        self.code_finder=code_finder
    def end_text_unit(self):
        super().end_text_unit()
        if self.code_finder is not None:
            event=self._events[-1]
            self._events[-1]=replace(event, resource=replace(event.resource, fragments=(self.code_finder.process(event.resource.fragments[0]),)))
        return event.resource
