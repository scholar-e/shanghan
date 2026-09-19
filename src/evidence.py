"""Request-local evidence identities and append-only citation numbering."""

import re


class EvidenceRegistry:
    def __init__(self):
        self._sources = []
        self._texts = []
        self._indices = {}

    def register(self, source, text):
        source_id = f"{source['type']}:{source['key']}"
        if source_id in self._indices:
            index = self._indices[source_id]
            # A subsequent tool may retrieve a fuller passage of the same source.
            if text and text not in self._texts[index]:
                self._texts[index] += "\n\n" + text
                if not source.get("hide_in_popup"):
                    self._sources[index]["content"] = self._texts[index]
            return index + 1
        index = len(self._sources)
        public = dict(source, source_id=source_id, citation_id=index + 1)
        if public.get("hide_in_popup"):
            public.pop("content", None)
        else:
            public["content"] = text
        self._indices[source_id] = index
        self._sources.append(public)
        self._texts.append(text)
        return index + 1

    @property
    def sources(self):
        return [dict(source) for source in self._sources]

    def context(self):
        return "\n\n".join(
            f"[{i}] {source['title']}\n{text}"
            for i, (source, text) in enumerate(zip(self._sources, self._texts), 1)
        )

    def source_list(self):
        return "\n".join(f"[{i}] {source['title']}" for i, source in enumerate(self._sources, 1))

    def validate_citations(self, answer):
        """Normalize citation groups and visibly flag references absent from evidence.

        This validates source identity, not whether a source supports a claim.
        Markdown links are left intact; their labels are not our citation syntax.
        """
        invalid = set()
        unavailable = "（来源不可用）" if re.search(r"[\u4e00-\u9fff]", answer) else "(source unavailable)"

        def replace(match):
            rendered = []
            for value in re.split(r"\s*[,，]\s*", match.group(1)):
                number = int(value)
                if 1 <= number <= len(self._sources):
                    rendered.append(f"[{number}]")
                else:
                    invalid.add(number)
                    rendered.append(unavailable)
            return "".join(rendered)

        cleaned = re.sub(r"\[(\d+(?:\s*[,，]\s*\d+)*)\](?!\()", replace, answer)
        return cleaned, sorted(invalid)
