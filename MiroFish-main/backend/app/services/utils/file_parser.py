class FileParser:
    def parse(self, *a, **kw): return {"content":"","type":"text"}
def split_text_into_chunks(text, chunk_size=1000): return [text[i:i+chunk_size] for i in range(0,len(text),chunk_size)]
