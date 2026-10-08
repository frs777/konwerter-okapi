import re
from core.document.model import Code, TextFragment

class InlineCodeFinder:
    TAGTYPE="regxph"
    def __init__(self,rules=()): self.rules=list(rules); self._compiled=[re.compile(r,re.MULTILINE) for r in self.rules]
    @classmethod
    def markdown_default(cls): return cls([r"\{\{[^}]+\}\}"])
    def add_rule(self,pattern): self.rules.append(pattern); self._compiled.append(re.compile(pattern,re.MULTILINE))
    def process(self,fragment):
        out=[]
        for part in fragment.parts:
            if not isinstance(part,str): out.append(part); continue
            matches=[]
            for rx in self._compiled: matches.extend(rx.finditer(part))
            matches.sort(key=lambda m:(m.start(),m.end()))
            last=0
            for m in matches:
                if m.start()<last: continue
                if m.start()>last: out.append(part[last:m.start()])
                out.append(Code(m.group(0),self.TAGTYPE)); last=m.end()
            if last<len(part): out.append(part[last:])
        return TextFragment(tuple(out))
